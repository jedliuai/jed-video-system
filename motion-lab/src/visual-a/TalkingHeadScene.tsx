import React from 'react';
import {AbsoluteFill, CanvasImage, staticFile} from 'remotion';
import {TalkingHeadOverlay} from '../live/TalkingHeadOverlay';
import {talkingHeadDefault, type TalkingHeadContent} from './content';

export type TalkingHeadSceneProps = {content?: TalkingHeadContent};

export const TalkingHeadScene: React.FC<TalkingHeadSceneProps> = ({content = talkingHeadDefault}) => {
  return <AbsoluteFill>
    <CanvasImage src={staticFile(content.background)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    <TalkingHeadOverlay content={content} />
  </AbsoluteFill>;
};
