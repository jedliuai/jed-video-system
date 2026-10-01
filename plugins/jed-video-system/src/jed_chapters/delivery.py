"""Reuse a specific accepted chapter recipe without approving a whole video."""
import hashlib
from pathlib import Path

from jed_review import evaluate_gate, validate_state


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def accepted_recipe(state, candidate_id, props_path, props):
    validate_state(state)
    candidate = state['candidates'][candidate_id]
    if candidate['scope'] != 'visual_sample' or 'add_chapter_transition' not in candidate['operations']:
        raise ValueError('A chapter visual sample acceptance is required')
    gate = evaluate_gate(state, candidate_id)
    if not gate['allowed']:
        raise ValueError('Chapter sample is not currently accepted')
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
        raise ValueError('Delivery props must be the exact accepted sample input')
    events = props.get('chapterTransitions', [])
    if not events or any(event.get('styleId') != candidate['patternId'] or
                         event.get('styleRevision') != candidate['revision'] for event in events):
        raise ValueError('Chapter recipe differs from the accepted style version')
    return {'chapterRecipeApproved': True, 'wholeVideoApproved': False,
            'projectId': state['projectId'], 'candidateId': candidate_id,
            'approvalRequestId': gate['approvalRequestId'], 'verifiedDependencies': paths}


def asset_props(props, event):
    """The same chapter component on a transparent canvas, at its local clock."""
    duration = event['durationInFrames']
    start = event['outputStartFrame']
    if type(duration) is not int or duration < 1 or type(start) is not int or start < 0 or start + duration > props['durationInFrames']:
        raise ValueError('Chapter event is outside the delivery timeline')
    if event.get('audioPolicy') != 'continue_source':
        raise ValueError('Only a cover with continuous source audio is implemented')
    return {'sourceSrc': props['sourceSrc'], 'fps': props['fps'], 'durationInFrames': duration,
            'clips': [], 'captions': [], 'overlays': [],
            'chapterTransitions': [{**event, 'outputStartFrame': 0}]}
