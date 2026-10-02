"""Replace approved alpha media in a copy of the latest saved draft.

Track data is never reconstructed. Existing Bridge owns codec, preservation
checks, publication locks, index backups and application-running checks.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import worker


def decoded_frame(path, frame):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf',
        f'select=eq(n\\,{frame}),format=rgba', '-frames:v', '1', '-f', 'rawvideo', '-'],
        capture_output=True, check=True, timeout=60).stdout


def relative_media(raw):
    relative = Path(raw)
    if relative.anchor or '..' in relative.parts:
        raise ValueError('Replacement paths must be relative to the draft copy')
    return relative


def compare_premultiplied_rgba(actual, straight):
    """Allow encoding error, never a new edge, alpha mask or design change.

    Fixed limits apply to visible pixels, so a mostly empty frame cannot dilute
    the error. This validates transport equivalence, not editor playback.
    """
    if not straight or len(actual) != len(straight) or len(straight) % 4:
        raise ValueError('Invalid decoded RGBA transport frame')
    if actual[3::4] != straight[3::4]:
        raise ValueError('Alpha transport changed the accepted transparency mask')
    maximum, total, count = 0.0, 0.0, 0
    for pixel, alpha in enumerate(straight[3::4]):
        if not alpha:
            continue
        offset = pixel * 4
        for channel in range(3):
            error = abs(actual[offset + channel] - straight[offset + channel] * alpha / 255)
            maximum = max(maximum, error)
            total += error
            count += 1
    if not count or maximum > 6 or total / count > 0.5:
        raise ValueError('Premultiplied replacement changes the accepted visible colors')
    return {'mode': 'premultiplied-rgb', 'alphaMaskMatches': True,
            'visibleRgbMaxError': maximum, 'visibleRgbMeanError': total / count}


def verify_acceptance(spec):
    state = worker.read_json(spec['reviewState'])
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugins/jed-video-system/src'))
    from jed_review import validate_state
    validate_state(state)
    request = next(r for r in state['requests'] if r['requestId'] == spec['approvalRequestId'])
    if request['status'] != 'approved' or request['candidateId'] != spec['candidateId']:
        raise ValueError('This candidate has no explicit acceptance')
    candidate = state['candidates'][request['candidateId']]
    if candidate['scope'] != 'visual_sample' or candidate['artifactKind'] != 'image' or candidate['scopeId'] != 'talking-head-edge-design-direction' or candidate['operations'] not in [['choose_fine_white_edge_design'], ['choose_none_white_edge_design']]:
        raise ValueError('Acceptance does not cover this text-edge design operation')
    if candidate['fingerprint'] != request['fingerprint']:
        raise ValueError('Accepted candidate revision changed')
    if worker.sha256(candidate['locator']) != candidate['artifactDigest']:
        raise ValueError('Accepted image changed')
    alpha = state['candidates'][spec['acceptedAlphaCandidateId']]
    if alpha['candidateId'] not in candidate['dependsOn'] or worker.sha256(alpha['locator']) != alpha['artifactDigest']:
        raise ValueError('Accepted alpha sample changed')
    actual = decoded_frame(spec['replacements'][0]['path'], spec['matchFrame'])
    expected = decoded_frame(alpha['locator'], 0)
    transport = spec.get('alphaTransport', 'straight')
    proof = None
    if transport == 'premultiplied-rgb':
        if candidate['operations'] != ['choose_none_white_edge_design']:
            raise ValueError('Alpha transport repair requires the accepted no-edge design')
        proof = compare_premultiplied_rgba(actual, expected)
    elif transport != 'straight':
        raise ValueError('Unsupported alpha transport')
    elif not actual or actual != expected:
        raise ValueError('Replacement does not reproduce the accepted decoded alpha frame')
    return {'candidateId': candidate['candidateId'], 'approvalRequestId': request['requestId'],
            'sampleDigest': candidate['artifactDigest'], 'decodedAlphaFrameMatches': actual == expected,
            'alphaTransportProof': proof,
            'targetEditorVerified': False}


def build(spec, publish=False):
    if spec.get('schemaVersion') != 'jed-overlay-replacement/1':
        raise ValueError('Unsupported replacement schema')
    Bridge, _, config = worker.import_bridge(spec)
    from jianying_bridge.core import digest, remap_paths, valid_name, within
    valid_name(spec['name'])
    invocation = Path(spec['outputRoot']).resolve() / uuid.uuid4().hex
    invocation.mkdir(parents=True, exist_ok=False)
    bridge = Bridge({**config, 'work_root': str(invocation / 'bridge-work')})
    if config.get('draft_root') and bridge.draft_root != Path(config['draft_root']).resolve():
        raise ValueError('Environment overrides the configured draft root')
    source = bridge.source(spec['sourceName'])
    if source.name.casefold() == spec['name'].casefold() or (bridge.draft_root / spec['name']).exists():
        raise ValueError('Replacement must create a distinct draft copy')
    try:
        acceptance = verify_acceptance(spec)
        bridge.reject_links(source)
        before = bridge.fingerprints(source)
        timeline, project = bridge.layout(source)
        original, _ = bridge.read(timeline)
        track = next(t for t in original['tracks'] if t['id'] == spec['trackId'])
        if track['type'] != 'video':
            raise ValueError('Replacement requires an explicit video track')
        material_ids = {s['material_id'] for s in track['segments']}
        owned = {Path(m['path']).resolve() for m in original['materials']['videos'] if m['id'] in material_ids}
        shared = {Path(m['path']).resolve() for m in original['materials']['videos']
                  if m['id'] in {s['material_id'] for t in original['tracks'] if t['id'] != track['id'] for s in t['segments']}}
        replacements = {}
        for item in spec['replacements']:
            relative = relative_media(item['relative'])
            old = within(source / relative, source)
            new = worker.existing_file(item['path'])
            if old not in owned or old in shared or old.suffix.lower() != '.mov' or relative.as_posix() in replacements:
                raise ValueError('Replacement is outside the selected alpha track or shared with another track')
            if worker.sha256(new) != item['sha256']:
                raise ValueError('Rendered replacement changed')
            old_info, new_info = worker.metadata(old), worker.metadata(new)
            for key in ['width', 'height', 'r_frame_rate', 'nb_frames', 'duration', 'codec_name', 'pix_fmt']:
                if old_info['video'].get(key) != new_info['video'].get(key):
                    raise ValueError(f'Replacement media changed {key}')
            if new_info['video'].get('profile') != '4444' or any(s['codec_type'] == 'audio' for s in new_info['streams']):
                raise ValueError('Expected silent ProRes 4444 alpha media')
            replacements[relative.as_posix()] = {'path': new, 'oldSha256': worker.sha256(old), 'newSha256': item['sha256']}
        if not replacements:
            raise ValueError('No replacement media specified')
        for path in bridge.core_files(source):
            if path == timeline or not path.relative_to(source).as_posix().startswith('Timelines/') or path.name not in {'draft_info.json', 'draft_content.json'}:
                continue
            other, _ = bridge.read(path)
            other_paths = {Path(m['path']).resolve() for m in other.get('materials', {}).get('videos', []) if m.get('path')}
            if any(source / relative in other_paths for relative in replacements):
                raise ValueError('Replacement media is shared with another saved timeline')
        original_files = {p.relative_to(source).as_posix(): worker.sha256(p)
                          for p in source.rglob('*') if p.is_file()}
        build_id = uuid.uuid4().hex
        directory = bridge.work / 'builds' / build_id
        target = directory / spec['name']
        shutil.copytree(source, target)
        copied = {p.relative_to(target).as_posix(): worker.sha256(p) for p in target.rglob('*') if p.is_file()}
        if copied != original_files or bridge.fingerprints(source) != before:
            raise ValueError('Latest saved draft changed during copy')
        files = {}
        draft_id = str(uuid.uuid4()).upper()
        main_relative = timeline.relative_to(source).as_posix()
        now = time.time_ns() // 1000
        for relative in before:
            raw = (source / relative).read_bytes()
            baseline = directory / 'baseline' / relative
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_bytes(raw)
            data, encrypted = bridge.read(source / relative)
            updated = remap_paths(data, source, target)
            if relative == 'draft_meta_info.json':
                updated.update(draft_id=draft_id, draft_name=spec['name'], draft_fold_path=target.as_posix(),
                               draft_root_path=bridge.draft_root.as_posix(), tm_draft_create=now, tm_draft_modified=now,
                               cloud_draft_sync=False)
                for field in ['tm_draft_cloud_entry_id', 'tm_draft_cloud_parent_entry_id', 'tm_draft_cloud_space_id', 'tm_draft_cloud_user_id']:
                    if field in updated:
                        updated[field] = -1
            elif relative == 'Timelines/project.json':
                updated.update(id=str(uuid.uuid4()).upper(), create_time=now, update_time=now)
            elif relative == main_relative and not project:
                updated['id'] = draft_id
            bridge.write(target / relative, updated, encrypted)
            files[relative] = {'encrypted': encrypted, 'baseline_sha256': digest(raw),
                               'expected_hash': bridge.semantic_hash(updated, target)}
        aliases = {r: main_relative for r in before if r != main_relative and before[r] == before[main_relative]}
        # Saved projects may also retain encrypted mirrors of draft_content.json.
        # Match exact bytes to a core file; do not guess at arbitrary temp files.
        for relative, old_digest in original_files.items():
            if Path(relative).name not in {'template-2.tmp', 'draft_content.json.bak', 'draft_info.json.bak'}:
                continue
            master = next((r for r, digest_value in before.items() if digest_value == old_digest), None)
            if master and relative not in files:
                aliases[relative] = master
        for alias, master in aliases.items():
            shutil.copy2(target / master, target / alias)
        sidecar_changes = []
        for path in target.rglob('*.json'):
            relative = path.relative_to(target).as_posix()
            if relative in files or '.backup' in path.parts:
                continue
            try:
                data = json.loads(path.read_bytes())
            except (ValueError, UnicodeError):
                continue
            updated = remap_paths(data, source, target)
            if updated != data:
                worker.write_json(path, updated)
                sidecar_changes.append(relative)
        for relative, item in replacements.items():
            shutil.copy2(item['path'], target / relative)
            if worker.sha256(target / relative) != item['newSha256']:
                raise ValueError('Rendered replacement changed while copying')
        for relative, old_digest in original_files.items():
            if relative not in files and relative not in aliases and relative not in sidecar_changes and relative not in replacements:
                if worker.sha256(target / relative) != old_digest:
                    raise ValueError('Unrelated file changed: ' + relative)
        if bridge.fingerprints(source) != before or any(worker.sha256(source / r) != h for r, h in original_files.items()):
            raise ValueError('Source draft changed before publication')
        manifest = {'build_id': build_id, 'plan_id': 'accepted-alpha-media-replacement', 'name': spec['name'],
            'source_name': spec['sourceName'], 'source_path': str(source), 'source_fingerprints': before,
            'timeline_relative': main_relative, 'legacy': not bool(project), 'draft_id': draft_id, 'files': files,
            'aliases': aliases, 'embedded_audio': [], 'new_track_ids': [], 'new_segment_ids': [],
            'sound_track_ids': [], 'track_mode': 'independent', 'consolidate_track_ids': []}
        worker.write_json(directory / 'manifest.json', manifest)
        verified = bridge.verify(build_id)
        result = {'schemaVersion': 'jed-overlay-replacement-result/1', 'name': spec['name'], 'buildId': build_id,
            'draftPath': str(target), 'sourceName': spec['sourceName'], 'sourceDraftModified': False, 'published': False,
            'acceptance': acceptance, 'checks': {'bridge': verified, 'allUnrelatedFilesPreserved': True,
                'uiPlayback': 'pending', 'uiSaveReopen': 'pending', 'editorExport': 'pending'},
            'replacements': [{k: str(v) for k, v in item.items()} | {'relative': r} for r, item in replacements.items()],
            'sourceFileHashes': original_files, 'bridgeManifest': str(directory / 'manifest.json')}
        if publish:
            # The Bridge verifies and publishes; it refuses to overwrite existing drafts.
            published = bridge.publish(build_id)
            final = Path(published['draft_path'])
            for relative, item in replacements.items():
                if worker.sha256(final / relative) != item['newSha256']:
                    raise ValueError('Published replacement differs from the rendered asset')
            readback, _ = bridge.read(final / main_relative)
            from jianying_bridge.core import check_preserved
            check_preserved(original, readback, source, final, legacy=not bool(project))
            result.update(published=True, draftPath=str(final), publication=published)
        worker.write_json(invocation / 'replacement-receipt.json', result)
        return result
    except Exception as exc:
        worker.write_json(invocation / 'failure-report.json', {'error': str(exc), 'type': type(exc).__name__, 'retained': str(invocation)})
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    result = build(worker.read_json(args.input), args.publish)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
