import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, staticFile} from 'remotion';
import {TalkingHeadOverlay, type TalkingHeadOverlayProps} from './TalkingHeadOverlay';

export type LiveVideoSource = {
  /** A public/ relative path or HTTP(S) URL. Local filesystem paths must be staged in public/. */
  src: string;
  /** Source trim, measured at the composition FPS, not the media's native FPS. */
  trimBeforeFrames: number;
  /** Scene length at the composition FPS. Playback speed stays at 1. */
  durationInFrames: number;
};

export type LiveTalkingHeadSceneProps = TalkingHeadOverlayProps & {
  source: LiveVideoSource;
  /** Preserve the embedded original audio at full volume by default. */
  volume?: number;
};

const sourceUrl = (src: string) => {
  if (/^https?:\/\//i.test(src)) return src;
  if (/^[A-Za-z]:[\\/]/.test(src) || src.startsWith('\\')) {
    throw new Error('Stage the source video inside motion-lab/public and use a public-relative source.src.');
  }
  return staticFile(src);
};

export const LiveTalkingHeadScene: React.FC<LiveTalkingHeadSceneProps> = ({source, volume = 1, ...overlayProps}) => {
  if (!Number.isInteger(source.trimBeforeFrames) || source.trimBeforeFrames < 0) {
    throw new Error('source.trimBeforeFrames must be a nonnegative integer at the composition FPS.');
  }
  if (!Number.isInteger(source.durationInFrames) || source.durationInFrames <= 0) {
    throw new Error('source.durationInFrames must be a positive integer at the composition FPS.');
  }
  return <Sequence durationInFrames={source.durationInFrames}>
    <AbsoluteFill>
      <OffthreadVideo
        src={sourceUrl(source.src)}
        trimBefore={source.trimBeforeFrames}
        durationInFrames={source.durationInFrames}
        volume={volume}
        style={{width: '100%', height: '100%', objectFit: 'cover'}}
      />
      <TalkingHeadOverlay {...overlayProps} />
    </AbsoluteFill>
  </Sequence>;
};
