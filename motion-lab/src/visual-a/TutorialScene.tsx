import React from 'react';
import {AbsoluteFill, CanvasImage, Easing, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Eyebrow, SceneHeader, StepList, SubtleGrid} from './components';
import {tutorialDefault, type TutorialContent} from './content';
import {jedTokens as t} from './tokens';

export type TutorialSceneProps = {content?: TutorialContent};

export const TutorialScene: React.FC<TutorialSceneProps> = ({content = tutorialDefault}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: t.ink, color: t.white, fontFamily: t.font}}>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 90% 90%, rgba(45,107,255,0.15), transparent 65%)'}} />
    <SubtleGrid />
    <SceneHeader chapters={content.chapters} activeIndex={content.chapterIndex} />
    <div style={{position: 'absolute', left: t.safeX, top: 145}}><Eyebrow>{content.eyebrow}</Eyebrow><div style={{fontSize: 64, lineHeight: 1.4, marginTop: 21, fontWeight: 700, letterSpacing: -1}}>{content.headline}</div></div>
    <div style={{position: 'absolute', left: t.safeX, top: 370, width: 300}}><StepList steps={content.steps} /></div>
    <div style={{position: 'absolute', left: 510, top: 300, width: 1280, height: 720, borderRadius: 14, overflow: 'hidden', border: `1px solid ${t.line}`, boxShadow: '0 24px 80px rgba(0,0,0,0.35)', opacity: interpolate(frame, [0, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), translate: `0px ${interpolate(frame, [0, 22], [22, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)})}px`}}>
      <CanvasImage src={staticFile(content.background)} style={{width: '100%', height: '100%', objectFit: 'contain', background: t.deep}} />
    </div>
    <div style={{position: 'absolute', left: t.safeX, bottom: 60, width: 295, fontSize: 22, color: t.muted, lineHeight: 1.6}}>{content.note}</div>
  </AbsoluteFill>;
};
