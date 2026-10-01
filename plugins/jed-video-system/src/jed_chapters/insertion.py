"""Insert chapter-only intervals, preserving all original source frames.

Source/output clocks are explicit. This pilot inserts at safe caption and
motion boundaries; it refuses to restart a running animation silently.
"""
from copy import deepcopy


def insert_chapters(base, cards):
    fps, duration = base.get('fps'), base.get('durationInFrames')
    clips = base.get('clips', [])
    if fps != 30 or type(duration) is not int or duration <= 0:
        raise ValueError('Insertion pilot requires positive duration and 30fps')
    if len(clips) != 1 or clips[0].get('sourceStartFrame') != 0 or clips[0].get('outputStartFrame') != 0 or clips[0].get('durationInFrames') != duration:
        raise ValueError('Insertions currently start from an unchanged continuous source')
    if base.get('chapterTransitions') or base.get('timelineMode'):
        raise ValueError('Do not insert twice into an already mapped timeline')
    if not isinstance(cards, list) or not cards:
        raise ValueError('At least one explicit chapter insertion is required')
    result = deepcopy(base)
    result.update(timelineMode='chapter-insert', sourceDurationInFrames=duration,
                  clips=[], chapterTransitions=[], soundEffects=[], insertions=[])
    previous, offset, ids = 0, 0, set()
    for card in cards:
        boundary, length = card.get('sourceBoundaryFrame'), card.get('durationInFrames')
        if type(boundary) is not int or not previous < boundary < duration:
            raise ValueError('Insertion boundaries must be distinct ordered interior source frames')
        if type(length) is not int or not 36 <= length <= 90:
            raise ValueError('Chapter insertion needs 36..90 frames')
        if not isinstance(card.get('id'), str) or not card['id'] or card['id'] in ids:
            raise ValueError('Chapter insertion IDs must be distinct')
        if card.get('placement') != 'insert_hold' or card.get('audioPolicy') != 'pause_source':
            raise ValueError('Insertion must explicitly pause source and hold the chapter card')
        evidence = card.get('boundaryEvidence', {})
        if evidence.get('kind') != 'between_sentences' or not evidence.get('before') or not evidence.get('after'):
            raise ValueError('Use a verified sentence boundary with before/after speech')
        if any(item['startFrame'] < boundary < item['endFrame'] for item in base.get('captions', [])):
            raise ValueError('Insertion would split a caption phrase; choose a verified boundary')
        if any(item['outputStartFrame'] < boundary < item['outputStartFrame'] + item['durationInFrames'] for item in base.get('overlays', [])):
            raise ValueError('Insertion would interrupt an animation; compile a new motion mapping first')
        for field in ('title', 'number', 'artSrc', 'styleId', 'styleRevision'):
            if not isinstance(card.get(field), str) or not card[field].strip():
                raise ValueError(f'Missing editable chapter field {field}')
        sound = card.get('sound', {})
        sound_offset, sound_length = sound.get('offsetFrames'), sound.get('durationInFrames')
        if type(sound_offset) is not int or type(sound_length) is not int or sound_offset < 0 or sound_length < 1 or sound_offset + sound_length > length:
            raise ValueError('Sound must finish inside the silent chapter interval')
        if not isinstance(sound.get('audioSrc'), str) or not sound['audioSrc'] or sound.get('volume') != 1:
            raise ValueError('Use a prepared local sound asset with gain already applied')
        start = boundary + offset
        result['clips'].append({'id': f'source-{len(result["clips"])}',
            'sourceStartFrame': previous, 'outputStartFrame': previous + offset,
            'durationInFrames': boundary - previous})
        result['chapterTransitions'].append({key: card[key] for key in
            ('id', 'title', 'number', 'artSrc', 'styleId', 'styleRevision', 'durationInFrames', 'audioPolicy', 'placement')} |
            {'sourceBoundaryFrame': boundary, 'outputStartFrame': start})
        result['soundEffects'].append({'id': card['id'] + '-sound', 'chapterId': card['id'],
            'audioSrc': sound['audioSrc'], 'volume': 1,
            'outputStartFrame': start + sound_offset, 'durationInFrames': sound_length})
        result['insertions'].append({'id': card['id'], 'sourceBoundaryFrame': boundary,
            'outputStartFrame': start, 'durationInFrames': length})
        ids.add(card['id'])
        previous, offset = boundary, offset + length
    result['clips'].append({'id': f'source-{len(result["clips"])}', 'sourceStartFrame': previous,
        'outputStartFrame': previous + offset, 'durationInFrames': duration - previous})
    def shift(frame):
        return sum(card['durationInFrames'] for card in cards if card['sourceBoundaryFrame'] <= frame)
    result['captions'] = [{**caption, 'startFrame': caption['startFrame'] + shift(caption['startFrame']),
        'endFrame': caption['endFrame'] + sum(card['durationInFrames'] for card in cards if card['sourceBoundaryFrame'] < caption['endFrame'])}
        for caption in base.get('captions', [])]
    result['overlays'] = [{**overlay, 'outputStartFrame': overlay['outputStartFrame'] + shift(overlay['outputStartFrame'])}
        for overlay in base.get('overlays', [])]
    result['durationInFrames'] = duration + offset
    result['chapterReview'] = {'status': 'candidate', 'humanApproved': False,
        'visualRecipeRetained': True, 'audioAndPacingApproved': False,
        'requiredSample': 'inserted_chapter_sound_with_before_after_speech'}
    validate_inserted_timeline(result)
    return result


def validate_inserted_timeline(props):
    if props.get('timelineMode') != 'chapter-insert' or props.get('fps') != 30:
        raise ValueError('Unsupported inserted timeline')
    clips, inserts = props.get('clips', []), props.get('insertions', [])
    if len(clips) != len(inserts) + 1 or not inserts:
        raise ValueError('Inserted timeline requires every source interval and gap')
    source_cursor, output_cursor = 0, 0
    for i, clip in enumerate(clips):
        length = clip.get('durationInFrames')
        if type(length) is not int or length <= 0 or clip.get('sourceStartFrame') != source_cursor or clip.get('outputStartFrame') != output_cursor:
            raise ValueError('Original frames must be preserved in order without loss or overlap')
        source_cursor += length
        output_cursor += length
        if i < len(inserts):
            gap = inserts[i]
            if gap.get('sourceBoundaryFrame') != source_cursor or gap.get('outputStartFrame') != output_cursor or type(gap.get('durationInFrames')) is not int or gap['durationInFrames'] <= 0:
                raise ValueError('Chapter gap does not match source/output mapping')
            output_cursor += gap['durationInFrames']
    if source_cursor != props.get('sourceDurationInFrames') or output_cursor != props.get('durationInFrames'):
        raise ValueError('Mapped timeline duration differs from preserved source and inserted gaps')
    ids = [gap['id'] for gap in inserts]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate chapter gap')
    events = props.get('chapterTransitions', [])
    if len(events) != len(inserts):
        raise ValueError('Every gap needs exactly one chapter card')
    for event, gap in zip(events, inserts):
        if any(event.get(key) != gap[key] for key in ('id', 'sourceBoundaryFrame', 'outputStartFrame', 'durationInFrames')) or event.get('audioPolicy') != 'pause_source' or event.get('placement') != 'insert_hold':
            raise ValueError('Chapter card differs from its gap')
    for item in props.get('captions', []):
        if any(item['startFrame'] < gap['outputStartFrame'] + gap['durationInFrames'] and item['endFrame'] > gap['outputStartFrame'] for gap in inserts):
            raise ValueError('Original captions cannot appear during a chapter-only gap')
    sounds = props.get('soundEffects', [])
    if len(sounds) != len(inserts) or {sound.get('chapterId') for sound in sounds} != set(ids):
        raise ValueError('Every gap needs exactly one short sound')
    for sound in sounds:
        matching = [gap for gap in inserts if gap['id'] == sound['chapterId']]
        if len(matching) != 1:
            raise ValueError('Sound has no unique chapter gap')
        gap = matching[0]
        if type(sound.get('durationInFrames')) is not int or sound['durationInFrames'] <= 0 or type(sound.get('outputStartFrame')) is not int or sound.get('volume') != 1 or sound['outputStartFrame'] < gap['outputStartFrame'] or sound['outputStartFrame'] + sound['durationInFrames'] > gap['outputStartFrame'] + gap['durationInFrames']:
            raise ValueError('Chapter sound would overlap source speech')
    return props
