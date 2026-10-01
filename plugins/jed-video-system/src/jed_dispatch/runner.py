"""Fixed local actions; official plugins and external repositories stay untouched."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from jed_review import evaluate_gate, validate_state
from jed_routing import route_project


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def local_path(root, value):
    if not isinstance(value, str) or not value or '://' in value:
        raise ValueError('Expected a local path')
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def _review(state, candidate_id, project_id, bundle):
    validate_state(state)
    if state['projectId'] != project_id:
        raise ValueError('Review projectId differs from dispatch projectId')
    candidate = state['candidates'][candidate_id]
    if candidate['scope'] != 'rough_cut':
        raise ValueError('Applying a draft requires the concrete rough_cut version, not a style approval')
    decision = evaluate_gate(state, candidate_id)
    if not decision['allowed']:
        raise ValueError('Review gate is not approved: ' + decision['status'])
    covered, visited = {}, set()
    def inspect(key):
        if key in visited:
            return
        visited.add(key)
        item = state['candidates'][key]
        path = Path(item['locator'])
        if not path.is_absolute() or not path.is_file() or sha(path) != item['artifactDigest']:
            raise ValueError('Review artifact or dependency changed/missing')
        covered[str(path.resolve())] = item['artifactDigest']
        for dependency in item['dependsOn']:
            inspect(dependency)
    inspect(candidate_id)
    if any(covered.get(path) != digest for path, digest in bundle.items()):
        raise ValueError('Review must bind all current props, source, fonts and overlay inputs')
    return decision


def _prepare(root, request, capabilities):
    if request.get('schemaVersion') != '0.1.0':
        raise ValueError('Unsupported dispatch schemaVersion')
    job_id = request.get('jobId', '')
    if not isinstance(job_id, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', job_id):
        raise ValueError('jobId must be a simple bounded name')
    action = request.get('action')
    if action not in ('remotion-still', 'create-isolated-draft'):
        raise ValueError('Unsupported local action; hosted tasks and publishing require a separate host workflow')
    phase = request.get('phase')
    if phase not in ('prepare', 'reviewed-apply'):
        raise ValueError('phase must be prepare or reviewed-apply')
    if action == 'remotion-still' and phase != 'prepare':
        raise ValueError('A static still only prepares evidence; it cannot apply video aesthetics')
    if action not in request.get('intent', {}).get('authorizedActions', []):
        raise ValueError('This exact local action lacks explicit project intent')
    project_id = request.get('projectId')
    route = route_project({'schemaVersion': '0.1.0', 'projectId': project_id,
        'destination': 'preview' if action == 'remotion-still' else 'jianying',
        'stages': ['motion'] if action == 'remotion-still' else ['assemble']}, capabilities)
    if route['status'] != 'route_ready':
        raise ValueError('Required backend capability is unavailable')
    config_path = local_path(root, request['localConfig'])
    config = read(config_path)
    props_path = local_path(root, request['renderProps'])
    props = read(props_path)
    duration = props.get('durationInFrames')
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0 or props.get('fps') != 30:
        raise ValueError('Pilot props require positive duration and 30fps')
    source_name = props.get('sourceSrc')
    if not isinstance(source_name, str) or Path(source_name).name != source_name:
        raise ValueError('Pilot source must be a simple public filename')
    # Only this project's fixed renderer is wired, never an arbitrary supplied repository.
    motion = root / 'motion-lab'
    source = motion / 'public' / source_name
    fonts = [motion / 'public/fonts/jed-sans-regular.ttf', motion / 'public/fonts/jed-sans-bold.ttf']
    inputs = [props_path, source, *fonts]
    implementation = [root / 'plugins/jed-video-system/src/jed_dispatch/runner.py']
    job_root = root / 'work/dispatch' / job_id
    if action == 'remotion-still':
        node = shutil.which('node')
        cli = motion / 'node_modules/@remotion/cli/remotion-cli.js'
        browser = local_path(root, config['remotion']['browserExecutable'])
        package = read(motion / 'node_modules/@remotion/cli/package.json')
        if not node or package.get('version') != '4.0.530' or not cli.is_file() or not browser.is_file():
            raise ValueError('Bound Remotion 4.0.530 CLI, Node and browser are required')
        frame = request.get('frame', 180)
        if isinstance(frame, bool) or not isinstance(frame, int) or not 0 <= frame < duration:
            raise ValueError('Frame lies outside the preview')
        output = job_root / 'preview.png'
        argv = [node, str(cli), 'still', 'ProductionPreview', str(output),
                '--props', str(props_path), f'--frame={frame}',
                '--browser-executable', str(browser), '--log=error']
        implementation += [motion / 'package-lock.json', motion / 'remotion.config.ts', *sorted((motion / 'src').rglob('*.*'))]
        runtime = [Path(node), cli, browser]
    else:
        # The existing wrapper has fixed source/overlay/props. Reject other inputs.
        if props_path != (root / 'work/plans/live-render-props.json').resolve() or source_name != 'live-source.mp4':
            raise ValueError('Draft pilot currently accepts only the existing verified live props/source')
        overlay = root / 'work/renders/talking-head-overlay.mov'
        inputs.append(overlay)
        pwsh = shutil.which('pwsh')
        python = local_path(root, config['jianying']['python'])
        bridge_config = local_path(root, config['jianying']['bridgeConfig'])
        bridge = local_path(root, config['jianying']['bridgeProject'])
        if not pwsh or not python.is_file() or not bridge_config.is_file() or not (bridge / 'jianying_bridge').is_dir():
            raise ValueError('Existing PowerShell and Jianying Bridge runtime/config are required')
        script = root / 'scripts/create-live-draft.ps1'
        argv = [pwsh, '-NoProfile', '-File', str(script), '-LocalConfig', str(config_path),
                '-OutputRoot', str(job_root / 'draft')]
        output = job_root / 'draft-result.json'
        implementation += [script, root / 'workers/draft-adapter/worker.py']
        runtime = [Path(pwsh), python, bridge_config]
    if any(not path.is_file() for path in inputs + implementation):
        raise ValueError('Required input/implementation file is missing')
    bundle = {str(path.resolve()): sha(path) for path in inputs}
    implementation_hashes = {str(path.resolve()): sha(path) for path in implementation}
    binding = {str(path.resolve()): sha(path) for path in [config_path, *runtime]}
    for path, digest in request.get('expectedInputHashes', {}).items():
        if bundle.get(str(local_path(root, path))) != digest:
            raise ValueError('Input differs from the expected reviewed revision')
    gate = None
    if phase == 'reviewed-apply':
        gate = _review(read(local_path(root, request['reviewState'])), request['reviewCandidateId'], project_id, bundle)
    summary = {'action': action, 'phase': phase, 'projectId': project_id,
               'inputHashes': bundle, 'implementationHashes': implementation_hashes,
               'runtimeBindingHashes': binding, 'frame': request.get('frame'),
               'review': gate, 'route': route, 'output': str(output),
               'jobId': job_id}
    fingerprint = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()
    return summary, fingerprint, argv, motion if action == 'remotion-still' else root, job_root


def dispatch(root, request, capabilities, execute=False):
    """Plan by default. Execution calls only a static local action catalogue."""
    root = Path(root).resolve()
    summary, fingerprint, argv, cwd, job_root = _prepare(root, request, capabilities)
    result = {**summary, 'fingerprint': fingerprint, 'status': 'planned',
              'externalEditorVerified': False, 'humanApproved': summary['review'] is not None,
              'published': False}
    if not execute:
        return result
    receipts = job_root / 'receipt.json'
    try:
        job_root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        if not receipts.is_file():
            raise ValueError('Job directory already exists without a completed receipt; inspect before retrying')
        old = read(receipts)
        if old.get('fingerprint') != fingerprint:
            raise ValueError('jobId is already bound to different inputs/implementation')
        if old['status'] != 'succeeded':
            raise ValueError('Prior job did not succeed; inspect it instead of automatically repeating effects')
        if any(not Path(path).is_file() or sha(path) != digest for path, digest in old['outputHashes'].items()):
            raise ValueError('Completed output changed or is missing')
        return {**old, 'reused': True}
    result.update(status='running', command=argv)
    save(receipts, result)
    try:
        process = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=300, shell=False)
        (job_root / 'stdout.log').write_text(process.stdout, encoding='utf-8')
        (job_root / 'stderr.log').write_text(process.stderr, encoding='utf-8')
        if process.returncode != 0:
            raise ValueError(f'Local action failed with exit code {process.returncode}; see job logs')
        if any(sha(path) != digest for path, digest in summary['inputHashes'].items()):
            raise ValueError('Input changed during execution; result is not bound to the planned revision')
        output = Path(summary['output'])
        if summary['action'] == 'create-isolated-draft':
            evidence_lines = [line[10:].strip() for line in process.stdout.splitlines() if line.startswith('Evidence: ')]
            if len(evidence_lines) != 1:
                raise ValueError('Draft wrapper did not return one structured result path')
            evidence = Path(evidence_lines[0]).resolve()
            if not evidence.is_relative_to(job_root):
                raise ValueError('Draft result is outside the job workspace')
            data = read(evidence)
            if data.get('published') is not False:
                raise ValueError('Isolated draft unexpectedly reported publication')
            save(output, data)
            result['draftPath'] = data['draftPath']
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError('Action succeeded without a nonempty output')
        outputs = [p for p in job_root.rglob('*') if p.is_file() and p != receipts and p.suffix != '.log']
        result.update(status='succeeded', outputHashes={str(p.resolve()): sha(p) for p in outputs})
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        result.update(status='failed', error=str(exc))
    save(receipts, result)
    return result
