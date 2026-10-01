"""New isolated inserted draft, with independent native image/text/audio layers.

Uses the existing pinned fork for segments and existing Bridge for validation
and publication. No official plugin code or existing user draft is rewritten.
"""
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugins/jed-video-system/src'))
from jed_chapters.insertion import validate_inserted_timeline
from jed_chapters.editable import overlay_source_frame


def validate_layers(props, spec, worker):
    validate_inserted_timeline(props)
    if spec.get('schemaVersion') != 'jed-draft-inserted/1':
        raise ValueError('Unsupported editable insertion schema')
    worker.validate_spec({**spec, 'schemaVersion': 'jed-draft-probe/1', 'fps': props['fps'], 'durationFrames': props['durationInFrames']})
    for key, events in (('overlayMedia', props.get('overlays', [])),
                        ('chapterImages', props['chapterTransitions']), ('soundMedia', props['soundEffects'])):
        supplied = spec.get(key, [])
        if len(supplied) != len(events) or len({item['id'] for item in supplied}) != len(supplied) or {item['id'] for item in supplied} != {event['id'] for event in events}:
            raise ValueError(f'{key}: every event needs exactly one separate material')
        for item in supplied:
            event = next(event for event in events if event['id'] == item['id'])
            path = worker.existing_file(item['path'])
            if worker.sha256(path) != item.get('sha256') or worker.chapter_event_digest(event) != item.get('eventDigest'):
                raise ValueError(f'{key}: material or event differs from receipt')
            info = worker.metadata(path)
            video = info['video'] or {}
            if key == 'overlayMedia':
                overlay_source_frame(props, event)
                if video.get('codec_name') != 'prores' or not video.get('pix_fmt', '').startswith('yuva') or video.get('avg_frame_rate') != '30/1' or video.get('width') != 1920 or video.get('height') != 1080 or abs(info['durationUs'] - worker.frame_us(event['durationInFrames'], 30)) > 1000:
                    raise ValueError('Overlay requires an exact-duration 1080p/30fps alpha block')
            elif key == 'chapterImages':
                width, height = video.get('width', 0), video.get('height', 0)
                if path.suffix.lower() != '.png' or width < 1 or height < 1 or abs(width / height - 16/9) > .02:
                    raise ValueError('Chapter needs a native landscape PNG near the approved 16:9 ratio')
            elif not any(stream['codec_type'] == 'audio' for stream in info['streams']) or abs(info['durationUs'] - worker.frame_us(event['durationInFrames'], 30)) > 1000:
                raise ValueError('Sound material must match its short effective interval')
    previous = 0
    for caption in props.get('captions', []):
        start, end = caption['startFrame'], caption['endFrame']
        if type(start) is not int or type(end) is not int or not previous <= start < end <= props['durationInFrames'] or not isinstance(caption.get('text'), str) or not caption['text'].strip():
            raise ValueError('Editable captions must be ordered, nonempty and inside timeline')
        previous = end
    return props


def verify_layer_content(content, props, roles, worker):
    """Check actual saved materials and ranges, not merely our build manifest."""
    worker.structure_check(content, worker.frame_us(props['durationInFrames'], 30))
    tracks = {track['id']: track for track in content['tracks']}
    if set(tracks) != set(roles.values()):
        raise ValueError('Saved draft lost or gained an unexpected layer')
    def segments(role):
        return tracks[roles[role]]['segments']
    def ranges(role, expected):
        actual = segments(role)
        if len(actual) != len(expected):
            raise ValueError(f'{role}: saved segment count differs')
        for segment, item in zip(actual, expected):
            target = worker.span_us(item['outputStartFrame'], item['durationInFrames'], 30)
            if segment['target_timerange'] != target:
                raise ValueError(f'{role}: saved target clock differs')
    for role in ('footage', 'voice'):
        ranges(role, props['clips'])
        for segment, clip in zip(segments(role), props['clips']):
            if segment['source_timerange'] != worker.span_us(clip['sourceStartFrame'], clip['durationInFrames'], 30) or segment.get('volume') != (0 if role == 'footage' else 1):
                raise ValueError(f'{role}: source clock or voice separation differs')
    ranges('motion', props.get('overlays', []))
    for role in ('chapter-matte', 'chapter-art'):
        ranges(role, props['chapterTransitions'])
    ranges('sfx', props['soundEffects'])
    for role in ('chapter-number', 'chapter-title', 'chapter-brand', 'chapter-line'):
        ranges(role, props['chapterTransitions'])
    if any(segment.get('volume') != 0 for role in ('motion', 'chapter-matte', 'chapter-art') for segment in segments(role)):
        raise ValueError('Visual layers must not duplicate audio')
    for segment in segments('sfx'):
        if segment.get('volume') != 1 or segment['source_timerange']['start'] != 0:
            raise ValueError('Sound gain/range differs from the approved prepared asset')
    materials = {item['id']: item for item in content['materials']['texts']}
    def texts(role):
        return [json.loads(materials[segment['material_id']]['content'])['text'] for segment in segments(role)]
    ranges('captions', [{'outputStartFrame': item['startFrame'], 'durationInFrames': item['endFrame'] - item['startFrame']} for item in props.get('captions', [])])
    if texts('captions') != [item['text'] for item in props.get('captions', [])] or texts('chapter-title') != [item['title'] for item in props['chapterTransitions']] or texts('chapter-number') != [item['number'] for item in props['chapterTransitions']]:
        raise ValueError('Saved editable text differs from approved content')
    for material in materials.values():
        styles = json.loads(material['content']).get('styles', [])
        if not styles or any(not Path(style.get('font', {}).get('path', '')).is_file() for style in styles):
            raise ValueError('Every editable text style must retain its actual local font file')
    image_segments = segments('chapter-art')
    videos = {item['id']: item for item in content['materials']['videos']}
    for segment in image_segments:
        if videos[segment['material_id']].get('type') != 'photo' or not segment.get('common_keyframes'):
            raise ValueError('Chapter art must remain a native image with adjustable keyframes')
    if not all(Path(item['path']).is_file() for values in content['materials'].values() if isinstance(values, list) for item in values if isinstance(item, dict) and item.get('path') and item.get('type') in ('video', 'photo', 'extract_music', 'music')):
        raise ValueError('Inline draft references missing media')
    return {'status': 'passed', 'footageMuted': True, 'separateSourceVoice': True,
        'editableCaptionCount': len(segments('captions')), 'editableChapterTitles': len(segments('chapter-title')),
        'nativeChapterImages': len(image_segments), 'separateRemotionBlocks': len(segments('motion')),
        'soundEffectCount': len(segments('sfx')), 'frameMappingPreserved': True,
        'editorPlayback': 'pending_ui_verification'}


def build_inserted(spec, worker):
    props_path = worker.existing_file(spec['renderProps'])
    props = validate_layers(worker.read_json(props_path), spec, worker)
    source, voice, matte, regular, bold = [worker.existing_file(spec[key]) for key in ('source', 'voice', 'matte', 'font', 'boldFont')]
    if worker.metadata(source)['durationUs'] + 1000 < worker.frame_us(props['sourceDurationInFrames'], 30) or worker.metadata(voice)['durationUs'] + 1000 < worker.frame_us(props['sourceDurationInFrames'], 30):
        raise ValueError('Original footage and voice must cover the preserved source')
    Bridge, draft, bridge_config = worker.import_bridge(spec)
    from jianying_bridge.core import digest, remap_paths
    invocation = Path(spec['outputRoot']).resolve() / uuid.uuid4().hex
    invocation.mkdir(parents=True, exist_ok=False)
    try:
        stage = invocation / 'staging'
        stage.mkdir()
        folder = draft.DraftFolder(str(stage), user_data_path=str(invocation / 'isolated-user-data'))
        baseline_name = spec['name'] + '-baseline'
        script = folder.create_draft(baseline_name, 1920, 1080, 30, maintrack_adsorb=False)
        roles = {}
        def track(role, kind, label):
            value = script.append_track(draft.TrackSpec(kind, label))
            roles[role] = value.track_id
            return value
        base = track('footage', draft.TrackType.video, 'Jed · 底片（静音）')
        motion = track('motion', draft.TrackType.video, 'Jed · Remotion 透明模块')
        captions = track('captions', draft.TrackType.text, 'Jed · 可编辑字幕')
        plate = track('chapter-matte', draft.TrackType.video, 'Jed · 章节浅色底')
        image = track('chapter-art', draft.TrackType.video, 'Jed · 章节图片＋关键帧')
        number = track('chapter-number', draft.TrackType.text, 'Jed · 可编辑章节编号')
        title = track('chapter-title', draft.TrackType.text, 'Jed · 可编辑章节标题')
        brand = track('chapter-brand', draft.TrackType.text, 'Jed · 章节品牌')
        line = track('chapter-line', draft.TrackType.text, 'Jed · 蓝色装饰线')
        narration = track('voice', draft.TrackType.audio, 'Jed · 原始口播')
        sfx = track('sfx', draft.TrackType.audio, 'Jed · 短转场音效')
        def timerange(event):
            return draft.Timerange(**worker.span_us(event['outputStartFrame'], event['durationInFrames'], 30))
        for clip in props['clips']:
            source_range = draft.Timerange(**worker.span_us(clip['sourceStartFrame'], clip['durationInFrames'], 30))
            script.add_segment(draft.VideoSegment(str(source), timerange(clip), source_timerange=source_range, volume=0), base)
            script.add_segment(draft.AudioSegment(str(voice), timerange(clip), source_timerange=source_range, volume=1), narration)
        for event in props.get('overlays', []):
            item = next(item for item in spec['overlayMedia'] if item['id'] == event['id'])
            script.add_segment(draft.VideoSegment(item['path'], timerange(event), volume=0), motion)
        for caption in props.get('captions', []):
            event = {'outputStartFrame': caption['startFrame'], 'durationInFrames': caption['endFrame'] - caption['startFrame']}
            style = draft.TextStyle(size=5, color=(1, 1, 1), align=1)
            border = draft.TextBorder(width=8)
            native_style = style.export_style_range(0, len(caption['text']), border=border)
            native_style['font'] = {'id': '', 'path': str(regular)}
            script.add_segment(draft.TextSegment(caption['text'], timerange(event), font_path=str(regular),
                style=style, border=border, style_ranges=[native_style], clip_settings=draft.ClipSettings(transform_y=-.8)), captions)
        blue = (55/255, 107/255, 250/255)
        dark = (16/255, 33/255, 56/255)
        for event in props['chapterTransitions']:
            image_path = next(item['path'] for item in spec['chapterImages'] if item['id'] == event['id'])
            script.add_segment(draft.VideoSegment(str(matte), timerange(event), volume=0), plate)
            art = draft.VideoSegment(image_path, timerange(event), volume=0)
            # The accepted artwork stays a native photo; scale/opacity remain editable.
            for frame, alpha in ((0, 0), (5, 1), (event['durationInFrames']-7, 1), (event['durationInFrames']-1, 0)):
                art.add_keyframe(draft.KeyframeProperty.alpha, worker.frame_us(frame, 30), alpha)
            info = worker.metadata(image_path)['video']
            cover = max(info['width']/info['height']/(16/9), (16/9)/(info['width']/info['height']))
            art.add_keyframe(draft.KeyframeProperty.uniform_scale, 0, cover)
            art.add_keyframe(draft.KeyframeProperty.uniform_scale, worker.frame_us(event['durationInFrames']-1, 30), cover*1.012)
            script.add_segment(art, image)
            def text(value, size, cx, cy, color, target, moving=True):
                # Native text positioning is a first mapping; pixel fidelity is UI-pending.
                clip = draft.ClipSettings(transform_x=(cx-960)/960, transform_y=(540-cy)/540)
                style = draft.TextStyle(size=size/8, color=color, align=1, bold=True)
                native_style = style.export_style_range(0, len(value))
                native_style['font'] = {'id': '', 'path': str(bold)}
                styles = [native_style]
                if value == 'Jed .':
                    native_style['range'] = [0, 4]
                    dot_style = draft.TextStyle(size=size/8, color=blue, align=1, bold=True).export_style_range(4, 5)
                    dot_style['font'] = {'id': '', 'path': str(bold)}
                    styles.append(dot_style)
                segment = draft.TextSegment(value, timerange(event), font_path=str(bold),
                    style=style, style_ranges=styles, clip_settings=clip)
                segment.add_animation(draft.TextIntro.渐显, duration=worker.frame_us(8 if moving else 5, 30))
                segment.add_animation(draft.TextOutro.渐隐, duration=worker.frame_us(7, 30))
                if moving:
                    for frame in range(2, 9):
                        progress = 1 - (1 - (frame-2)/6)**3
                        segment.add_keyframe(draft.KeyframeProperty.position_y, worker.frame_us(frame, 30), (540-cy-(1-progress)*16)/540)
                script.add_segment(segment, target)
            text(event['number'], 78, 188, 324, blue, number)
            text(event['title'], 110, 144 + len(event['title'])*110/2, 503, dark, title)
            text('Jed .', 30, 150, 102, dark, brand, moving=False)
            text('━', 68, 178, 397, blue, line)
        for event in props['soundEffects']:
            item = next(item for item in spec['soundMedia'] if item['id'] == event['id'])
            script.add_segment(draft.AudioSegment(item['path'], timerange(event), volume=1), sfx)
        script.save(inline_materials=True)
        baseline = stage / baseline_name
        bridge = Bridge({**bridge_config, 'draft_root': str(stage), 'work_root': str(invocation / 'bridge-work')})
        if bridge.draft_root != stage.resolve():
            raise ValueError('Environment overrides isolated draft stage')
        worker.set_publication_root(bridge, baseline, bridge_config.get('draft_root'))
        # Same existing neutral Bridge handoff as preview; no fictitious audio addition.
        build_id = uuid.uuid4().hex
        build_dir = bridge.work / 'builds' / build_id
        target = build_dir / spec['name']
        shutil.copytree(baseline, target)
        (build_dir / 'baseline').mkdir()
        files = {}
        for relative in ('draft_info.json', 'draft_meta_info.json'):
            raw = (baseline / relative).read_bytes()
            (build_dir / 'baseline' / relative).write_bytes(raw)
            data, encrypted = bridge.read(baseline / relative)
            updated = remap_paths(data, baseline, target)
            if relative == 'draft_meta_info.json':
                updated['draft_name'] = spec['name']
            bridge.write(target / relative, updated, encrypted)
            files[relative] = {'encrypted': encrypted, 'baseline_sha256': digest(raw), 'expected_hash': bridge.semantic_hash(updated, target)}
        content, _ = bridge.read(target / 'draft_info.json')
        duration = worker.frame_us(props['durationInFrames'], 30)
        structural = worker.structure_check(content, duration)
        layers = verify_layer_content(content, props, roles, worker)
        transfer = {'build_id': build_id, 'plan_id': 'editable-inserted-preview', 'name': spec['name'],
            'source_name': baseline_name, 'source_path': str(baseline), 'source_fingerprints': bridge.fingerprints(baseline),
            'timeline_relative': 'draft_info.json', 'legacy': True, 'draft_id': content['id'], 'files': files,
            'aliases': {}, 'embedded_audio': [], 'new_track_ids': [], 'new_segment_ids': [],
            'sound_track_ids': [], 'track_mode': 'independent', 'consolidate_track_ids': []}
        worker.write_json(build_dir / 'manifest.json', transfer)
        verified = bridge.verify(build_id)
        result = {'schemaVersion': 'jed-draft-result/1', 'mode': 'editable-inserted', 'name': spec['name'],
            'buildId': build_id, 'draftId': content['id'], 'draftPath': str(target), 'published': False,
            'sourceDraftModified': False, 'durationFrames': props['durationInFrames'], 'durationUs': duration,
            'bridgeManifest': str(build_dir / 'manifest.json'), 'roleTrackIds': roles,
            'renderProps': str(props_path), 'renderPropsSha256': worker.sha256(props_path),
            'checks': {'structure': structural, 'layers': layers, 'bridge': verified,
                'uiPlayback': 'pending', 'uiSaveReopen': 'pending', 'editorExport': 'pending'},
            'editability': {'nativeCaptions': True, 'nativeChapterTitleAndNumber': True, 'nativeChapterImageAndKeyframes': True,
                'separateVoiceAndSound': True, 'separateRemotionBlocks': True, 'remotionInternalGraphicsEditableInEditor': False,
                'nativeTextPixelAccuracy': 'pending_ui_verification'}}
        manifest_path = invocation / 'draft-manifest.json'
        worker.write_json(manifest_path, result)
        return {'manifest': str(manifest_path), **result}
    except Exception as exc:
        worker.write_json(invocation / 'failure-report.json', {'error': str(exc), 'type': type(exc).__name__})
        raise
