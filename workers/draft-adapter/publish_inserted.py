"""Publish only a verified isolated inserted build through the existing Bridge."""
import argparse
import contextlib
import json
from pathlib import Path
import sys
import worker
from inserted import verify_layer_content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    spec = worker.read_json(args.input)
    result = spec['draftResult']
    if result.get('mode') != 'editable-inserted' or result.get('published') is not False or result['checks']['layers']['status'] != 'passed':
        raise ValueError('Requires a verified unpublished editable insertion build')
    Bridge, _, config = worker.import_bridge(spec)
    build_dir = Path(result['bridgeManifest']).resolve().parent
    config = {**config, 'work_root': str(build_dir.parents[1])}
    bridge = Bridge(config)
    if config.get('draft_root') and bridge.draft_root != Path(config['draft_root']).resolve():
        raise ValueError('Environment overrides configured publication root')
    with contextlib.redirect_stdout(sys.stderr):
        bridge.verify(result['buildId'])
        props = worker.read_json(result['renderProps'])
        if worker.sha256(result['renderProps']) != result['renderPropsSha256']:
            raise ValueError('Insertion props changed before publication')
        content, _ = bridge.read(Path(result['draftPath']) / 'draft_info.json')
        verify_layer_content(content, props, result['roleTrackIds'], worker)
        published = bridge.publish(result['buildId'])
        content, _ = bridge.read(Path(published['draft_path']) / 'draft_info.json')
        published['editableLayerChecks'] = verify_layer_content(content, props, result['roleTrackIds'], worker)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(published, ensure_ascii=False))


if __name__ == '__main__':
    main()
