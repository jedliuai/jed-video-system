"""Validate semantic chapter evidence and compile independent preview overlays.

The host analyzes speech and footage. This module does not infer a narrative
from timestamps or turn a candidate style into a human-approved edit.
"""
from copy import deepcopy
import re


def compile_chapters(structure, props, props_digest, source_digest):
    if structure.get('schemaVersion') != '0.1.0':
        raise ValueError('Unsupported chapter structure version')
    source = structure['source']
    duration = props['durationInFrames']
    if source['publicFile'] != props['sourceSrc'] or source['mediaSha256'] != source_digest:
        raise ValueError('Chapter source differs from actual media')
    if structure['sourcePropsSha256'] != props_digest:
        raise ValueError('Timeline props changed; reconsider chapter boundaries')
    if source['fps'] != 30 or props.get('fps') != 30 or source['durationInFrames'] != duration:
        raise ValueError('Chapter pilot requires the same 30fps timeline')
    clips = props['clips']
    if len(clips) != 1 or clips[0]['sourceStartFrame'] != 0 or clips[0]['outputStartFrame'] != 0 or clips[0]['durationInFrames'] != duration:
        raise ValueError('Chapter pilot requires an unchanged continuous source; compile a new mapping for edited timelines')
    style = structure['style']
    for field in ('id', 'revision', 'referenceAsset', 'imageBackend'):
        if not isinstance(style.get(field), str) or not style[field].strip():
            raise ValueError(f'Missing style {field}')
    if not re.fullmatch(r'[0-9a-f]{64}', style.get('referenceSha256', '')):
        raise ValueError('Style reference requires a SHA-256 digest')
    if style['referenceAsset'].startswith(('/', '\\')) or '..' in style['referenceAsset'].replace('\\', '/').split('/') or '://' in style['referenceAsset']:
        raise ValueError('Style reference must be a local public asset')
    sections = structure['sections']
    if not sections:
        raise ValueError('No evidenced sections')
    result = deepcopy(props)
    events, seen = [], set()
    previous_end = 0
    for section in sections:
        key = section['id']
        start, end = section['startFrame'], section['endFrame']
        if key in seen or isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= duration or start < previous_end:
            raise ValueError('Sections must be unique, ordered, nonoverlapping frame ranges')
        seen.add(key)
        previous_end = end
        if section['kind'] not in ('context', 'overview', 'explanation', 'demonstration', 'summary'):
            raise ValueError('Unknown semantic chapter kind')
        if not isinstance(section.get('summary'), str) or not section['summary'].strip():
            raise ValueError('Each chapter needs a source-grounded summary')
        evidence = section.get('evidence', {})
        quote = evidence.get('quote')
        confidence = evidence.get('confidence')
        if not isinstance(quote, str) or not quote.strip() or isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not 0 <= confidence <= 1:
            raise ValueError('Chapter needs a quote and boundary confidence')
        if evidence.get('atFrame') != start:
            raise ValueError('Boundary evidence must identify the proposed source frame')
        title = section['title']
        if not isinstance(title, str) or not 1 <= len(title) <= 12:
            raise ValueError('Chapter title must be short and nonempty')
        transition = section.get('transition')
        if not transition:
            continue
        if confidence < 0.8:
            raise ValueError('Uncertain chapter boundary needs content review before rendering')
        length = transition['durationInFrames']
        if not isinstance(transition.get('number'), str) or not re.fullmatch(r'[0-9]{2}', transition['number']):
            raise ValueError('Transition number must be two editable digits')
        if isinstance(length, bool) or not isinstance(length, int) or not 36 <= length <= 90 or start + length > end:
            raise ValueError('Transition needs 36..90 frames within the chapter')
        if transition.get('audioPolicy') != 'continue_source' or transition.get('placement') != 'cover_bridge':
            raise ValueError('Pause/insert changes the timeline and needs a separate mapping; this pilot only covers a spoken bridge')
        bridge = section.get('bridge')
        if not bridge or bridge.get('kind') != 'spoken_bridge' or bridge['startFrame'] != start or bridge['endFrame'] < start + length:
            raise ValueError('Transition would cover content outside the verified spoken bridge')
        events.append({'id': key, 'title': title, 'number': transition['number'],
            'outputStartFrame': start, 'durationInFrames': length,
            'artSrc': style['referenceAsset'], 'styleId': style['id'],
            'styleRevision': style['revision'], 'audioPolicy': 'continue_source'})
    result['chapterTransitions'] = events
    result['chapterReview'] = {'humanApproved': False, 'status': 'candidate',
        'styleId': style['id'], 'styleRevision': style['revision'],
        'referenceSha256': style['referenceSha256'],
        'sourcePropsSha256': props_digest, 'sourceSha256': source_digest,
        'requiredSample': 'video_with_source_audio_and_before_after_context'}
    return result
