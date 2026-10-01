import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {ChapterTransitionPreview, type ChapterProps} from './ChapterTransition';

type SoundEvent = {id: string; audioSrc: string; outputStartFrame: number; durationInFrames: number; volume: number};
export type ChapterInsertProps = ChapterProps & {soundEffects: SoundEvent[]};

/** Source sequences leave real gaps; the chapter card and sound fill them. */
export const ChapterInsertPreview: React.FC<ChapterInsertProps> = (props) => <AbsoluteFill style={{backgroundColor: '#F7F5EF'}}>
  <ChapterTransitionPreview {...props} />
  {props.soundEffects.map(sound => <Sequence key={sound.id} from={sound.outputStartFrame} durationInFrames={sound.durationInFrames}>
    <Audio src={staticFile(sound.audioSrc)} volume={sound.volume} />
  </Sequence>)}
</AbsoluteFill>;
