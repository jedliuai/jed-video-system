import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {ArrowMark, ComparisonBars, Eyebrow, SceneHeader, SubtleGrid} from './components';
import {comparisonDefault, type ComparisonContent} from './content';
import {jedTokens as t} from './tokens';

export type ComparisonSceneProps = {content?: ComparisonContent};

export const ComparisonScene: React.FC<ComparisonSceneProps> = ({content = comparisonDefault}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: t.ink, color: t.white, fontFamily: t.font}}>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 88% 10%, rgba(45,107,255,0.17), transparent 60%)'}} />
    <SubtleGrid />
    <SceneHeader chapters={content.chapters} activeIndex={content.chapterIndex} />
    <div style={{position: 'absolute', left: t.safeX, top: 178}}>
      <Eyebrow>{content.eyebrow}</Eyebrow>
      <div style={{fontSize: 74, fontWeight: 700, lineHeight: 1.35, letterSpacing: -1.5, marginTop: 24}}>{content.headline}</div>
      <div style={{fontSize: 29, color: t.muted, marginTop: 15, letterSpacing: 1}}>{content.subtitle}</div>
    </div>
    <div style={{position: 'absolute', left: t.safeX, right: t.safeX, top: 390}}><ComparisonBars items={content.items} maxValue={content.maxValue} unit={content.unit} /></div>
    <div style={{position: 'absolute', left: t.safeX + 302, bottom: 122, display: 'flex', alignItems: 'center', gap: 20, opacity: interpolate(frame, [content.takeawayCue, content.takeawayCue + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), translate: `0px ${interpolate(frame, [content.takeawayCue, content.takeawayCue + 18], [14, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px`}}><ArrowMark color={t.gold} size={36} /><span style={{fontSize: 37, fontWeight: 700, color: t.gold}}>{content.takeaway}</span></div>
    <div style={{position: 'absolute', left: t.safeX, bottom: 54, fontSize: 22, color: t.muted}}>{content.disclosure}</div>
    <div style={{position: 'absolute', right: t.safeX, bottom: 54, fontSize: 20, color: t.muted, letterSpacing: 2}}>02 / COMPARISON</div>
  </AbsoluteFill>;
};
