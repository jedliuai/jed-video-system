"""Capability-based planning. A route is never execution authorization."""
from copy import deepcopy

STAGES = ('transcribe', 'speech_edit', 'captions', 'motion', 'sound',
          'assemble', 'verify', 'export')
TARGETS = ('jianying', 'chatcut', 'preview')


def _available(capabilities, backend, feature):
    entry = capabilities.get(backend, {})
    return (entry.get('connected') is True and feature in entry.get('features', [])
            and isinstance(entry.get('evidence'), dict)
            and isinstance(entry['evidence'].get('source'), str)
            and bool(entry['evidence']['source'].strip())
            and isinstance(entry['evidence'].get('checkedAt'), str)
            and bool(entry['evidence']['checkedAt'].strip()))


def route_project(request, capabilities):
    """Use a fresh caller-supplied capability snapshot; do not discover or mutate."""
    if not isinstance(request, dict) or not isinstance(capabilities, dict):
        raise ValueError('Request and capabilities must be objects')
    if request.get('schemaVersion') != '0.1.0':
        raise ValueError('Unsupported routing schemaVersion')
    if not isinstance(request.get('projectId'), str) or not request['projectId'].strip():
        raise ValueError('projectId is required')
    target = request.get('destination')
    if target not in TARGETS:
        raise ValueError('Unsupported destination')
    motion_mode = request.get('motionMode', 'fixed')
    if motion_mode not in ('fixed', 'editable'):
        raise ValueError('Unsupported motionMode')
    stages = request.get('stages')
    if (not isinstance(stages, list) or not stages or
            any(not isinstance(s, str) or s not in STAGES for s in stages)
            or len(set(stages)) != len(stages)):
        raise ValueError('stages must be a nonempty unique list of supported stages')
    pins = request.get('backendOverrides', {})
    if not isinstance(pins, dict) or any(s not in stages for s in pins):
        raise ValueError('Backend overrides must refer to requested stages')
    if any(not isinstance(v, str) or not v for v in pins.values()):
        raise ValueError('Backend override values must be backend names')
    for name, entry in capabilities.items():
        if (not isinstance(name, str) or not isinstance(entry, dict)
                or not isinstance(entry.get('connected'), bool)
                or not isinstance(entry.get('features'), list)
                or any(not isinstance(f, str) for f in entry['features'])):
            raise ValueError('Invalid capability snapshot entry')

    # Destination owns the timeline. Do not silently migrate to another editor.
    routes = {
        'transcribe': [('chatcut-hosted', 'transcription'), ('video-use', 'transcription')]
            if target == 'chatcut' else [('video-use', 'transcription')],
        'speech_edit': [('chatcut-hosted', 'script-edit')],
        'motion': [('remotion', 'fixed-motion')] if motion_mode == 'fixed'
            else [('chatcut-hosted', 'editable-motion')],
    }
    if target == 'chatcut':
        routes.update({
            'captions': [('chatcut-hosted', 'captions')],
            'sound': [('chatcut-hosted', 'audio-placement')],
            'assemble': [('chatcut-hosted', 'editable-timeline')],
            'verify': [('chatcut-hosted', 'composed-preview')],
            'export': [('chatcut-hosted', 'video-export')],
        })
    elif target == 'jianying':
        routes.update({
            'captions': [('jianying-draft', 'editable-captions')],
            'sound': [('jianying-cli', 'sound-copy')],
            'assemble': [('jianying-draft', 'draft-assembly')],
            'verify': [('jianying-ui', 'playback-save-reopen')],
            'export': [('jianying-ui', 'native-export')],
        })
    else:
        routes.update({
            'captions': [('remotion', 'preview-captions')],
            'sound': [],  # A new audio mix has not been integrated in the pilot.
            'assemble': [('remotion', 'video-preview')],
            'verify': [('local-verification', 'media-and-clock-check')],
            'export': [('remotion', 'video-preview')],
        })

    decisions, blockers = [], []
    for stage in STAGES:
        if stage not in stages:
            continue
        options = routes[stage]
        pin = pins.get(stage)
        if pin:
            options = [option for option in options if option[0] == pin]
        selected = next(((b, f) for b, f in options if _available(capabilities, b, f)), None)
        reason = None
        if not selected:
            reason = 'requested_backend_unavailable' if pin else 'no_validated_backend'
        elif stage == 'speech_edit' and target != 'chatcut':
            if not _available(capabilities, 'chatcut-handoff', 'source-time-mapping'):
                reason = 'speech_handoff_mapping_not_implemented'
        elif stage == 'transcribe' and target == 'chatcut' and selected[0] == 'video-use':
            if not _available(capabilities, 'chatcut-handoff', 'transcript-import'):
                reason = 'external_transcript_import_not_verified'
        elif stage == 'motion' and motion_mode == 'fixed' and target == 'chatcut':
            if not _available(capabilities, 'chatcut-handoff', 'original-and-overlay-import'):
                reason = 'separate_overlay_import_not_verified'
        elif stage == 'motion' and motion_mode == 'editable' and target != 'chatcut':
            if not _available(capabilities, 'chatcut-handoff', 'alpha-graphic-export'):
                reason = 'alpha_graphic_handoff_not_verified'
        if reason:
            blockers.append({'stage': stage, 'reason': reason})
        decisions.append({'stage': stage, 'backend': selected[0] if selected else None,
                          'feature': selected[1] if selected else None,
                          'status': 'blocked' if reason else 'selected',
                          'reason': reason})
    return {'schemaVersion': '0.1.0', 'projectId': request['projectId'],
            'destination': target, 'timelineOwner': target,
            'status': 'blocked' if blockers else 'route_ready',
            'routes': decisions, 'blockers': blockers,
            'executionAuthorized': False,
            'capabilityEvidence': {name: deepcopy(entry.get('evidence'))
                                   for name, entry in capabilities.items()},
            'note': '路线选择只说明后端与接口可用；需要另行满足项目约束、小样确认和实际工具的授权。'}
