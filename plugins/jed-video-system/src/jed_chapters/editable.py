"""Version-bound acceptance and per-layer mapping for editable chapter delivery."""
from pathlib import Path
from jed_review import evaluate_gate, validate_state
from .delivery import sha
from .insertion import validate_inserted_timeline


def accepted_insertion(state, candidate_id, props_path, props):
    validate_state(state)
    validate_inserted_timeline(props)
    candidate = state['candidates'][candidate_id]
    if candidate['scope'] != 'audio_sample' or 'insert_chapter_with_sound' not in candidate['operations']:
        raise ValueError('Requires the actual inserted chapter sound/pacing sample')
    gate = evaluate_gate(state, candidate_id)
    if not gate['allowed']:
        raise ValueError('Inserted chapter sample is not currently accepted')
    paths, visited = {}, set()
    def inspect(key):
        if key in visited:
            return
        visited.add(key)
        item = state['candidates'][key]
        path = Path(item['locator'])
        if not path.is_absolute() or not path.is_file() or sha(path) != item['artifactDigest']:
            raise ValueError('Accepted sample or dependency changed/missing')
        paths[str(path.resolve())] = item['artifactDigest']
        for dependency in item['dependsOn']:
            inspect(dependency)
    inspect(candidate_id)
    if paths.get(str(Path(props_path).resolve())) != sha(props_path):
        raise ValueError('Delivery props must be the exact accepted insertion input')
    return {'chapterSoundAndPacingApproved': True, 'wholeVideoApproved': False,
        'candidateId': candidate_id, 'approvalRequestId': gate['approvalRequestId'],
        'verifiedDependencies': paths}


def overlay_source_frame(props, event):
    """Map a complete overlay block back into its original continuous alpha asset."""
    start, length = event['outputStartFrame'], event['durationInFrames']
    if type(start) is not int or type(length) is not int or length <= 0:
        raise ValueError('Overlay needs a positive integer frame interval')
    matches = [clip for clip in props['clips'] if clip['outputStartFrame'] <= start and
        start + length <= clip['outputStartFrame'] + clip['durationInFrames']]
    if len(matches) != 1:
        raise ValueError('Overlay cannot cross a chapter gap or source boundary')
    clip = matches[0]
    return clip['sourceStartFrame'] + start - clip['outputStartFrame']
