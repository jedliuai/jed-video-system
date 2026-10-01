import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {Eyebrow, KeyPointCard, SceneHeader} from '../visual-a/components';
import {talkingHeadDefault, type TalkingHeadContent} from '../visual-a/content';
import {jedTokens as t} from '../visual-a/tokens';

/** Editorial data has no dependency on a background image or video file. */
export type TalkingHeadOverlayContent = Omit<TalkingHeadContent, 'background'>;
export type TalkingHeadOverlayProps = {
  content?: TalkingHeadOverlayContent;
  headlineCueFrame?: number;
  showHeader?: boolean;
  showFooter?: boolean;
};

/** A transparent, silent layer. All cue frames are relative to this layer's start. */
export const TalkingHeadOverlay: React.FC<TalkingHeadOverlayProps> = ({
  content = talkingHeadDefault,
  headlineCueFrame = 4,
  showHeader = true,
  showFooter = true,
}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill className="jed-talking-head-overlay" style={{color: t.ink, fontFamily: t.font, textShadow: t.photoTextShadow, pointerEvents: 'none'}}>
    <style>{`.jed-talking-head-overlay * {text-shadow: ${t.photoTextShadow}; -webkit-text-stroke: ${t.photoTextStroke}; paint-order: stroke fill;}`}</style>
    {showHeader ? <SceneHeader chapters={content.chapters} activeIndex={content.chapterIndex} surface="photo" /> : null}
    <div style={{position: 'absolute', left: t.safeX, top: 225, width: 670}}>
      <Eyebrow surface="photo">{content.eyebrow}</Eyebrow>
      <div style={{marginTop: 31, fontSize: 72, fontWeight: 700, lineHeight: 1.32, letterSpacing: -1.5}}>
        {content.headline.map((line, i) => <div key={`${i}-${line}`} style={{color: i === content.headline.length - 1 ? t.blue : t.ink, opacity: interpolate(frame, [headlineCueFrame + i * 7, headlineCueFrame + 18 + i * 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)}), translate: `0px ${interpolate(frame, [headlineCueFrame + i * 7, headlineCueFrame + 18 + i * 7], [24, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px`}}>{line}</div>)}
      </div>
      <div style={{display: 'flex', flexDirection: 'column', gap: 37, marginTop: 51}}>{content.points.map((point, i) => <KeyPointCard key={`${i}-${point.title}`} point={point} index={i} surface="photo" />)}</div>
    </div>
    {showFooter ? <div style={{position: 'absolute', left: t.safeX, bottom: 120, color: t.photoMuted, fontSize: 23, letterSpacing: 2, display: 'flex', gap: 17, alignItems: 'center'}}><span style={{width: 48, height: 2, background: t.blue}} />{content.footer}</div> : null}
  </AbsoluteFill>;
};
