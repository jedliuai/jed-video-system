"""Build audio from the source clock plus silent gaps, never by muting speech."""
from .insertion import validate_inserted_timeline


def audio_filter(props):
    """Input 0 is raw video, 1 original source, 2..N prepared chapter sounds.

    Source samples remain at 1x speed and gain. Silence is concatenated between
    source intervals; sound events fit entirely inside those gaps.
    """
    validate_inserted_timeline(props)
    fps = props['fps']
    clips = props['clips']
    filters = ['[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=' +
               str(len(clips)) + ''.join(f'[source{i}]' for i in range(len(clips)))]
    order = []
    for i, clip in enumerate(clips):
        start = clip['sourceStartFrame'] * 48000 // fps
        length = clip['durationInFrames'] * 48000 // fps
        filters.append(f'[source{i}]atrim=start_sample={start}:end_sample={start + length},'
                       f'asetpts=PTS-STARTPTS,apad,atrim=end_sample={length}[voice{i}]')
        order.append(f'[voice{i}]')
        if i < len(props['insertions']):
            samples = props['insertions'][i]['durationInFrames'] * 48000 // fps
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=end_sample={samples},asetpts=PTS-STARTPTS[gap{i}]')
            order.append(f'[gap{i}]')
    filters.append(''.join(order) + f'concat=n={len(order)}:v=0:a=1[speech]')
    for i, sound in enumerate(props['soundEffects']):
        samples = sound['durationInFrames'] * 48000 // fps
        delay = sound['outputStartFrame'] * 48000 // fps
        filters.append(f'[{i + 2}:a]aresample=48000,aformat=channel_layouts=stereo,'
                       f'atrim=end_sample={samples},asetpts=PTS-STARTPTS,adelay={delay}S:all=1[sfx{i}]')
    filters.append('[speech]' + ''.join(f'[sfx{i}]' for i in range(len(props['soundEffects']))) +
                   f'amix=inputs={len(props["soundEffects"]) + 1}:normalize=0:duration=first[outa]')
    return ';'.join(filters)
