import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';
import type {BarDatum, Chapter, KeyPoint, StepDatum} from './content';
import {jedTokens as t} from './tokens';

const enter = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1)} as const;

export const ArrowMark: React.FC<{color?: string; size?: number}> = ({color = t.cyan, size = 32}) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
    <path d="M5 16H25M18 8L26 16L18 24" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const BrandMark: React.FC = () => (
  <div style={{fontSize: 40, fontWeight: 700, letterSpacing: -1.5, display: 'flex', alignItems: 'center', gap: 9}}>
    Jed<span style={{width: 9, height: 9, borderRadius: '50%', background: t.blue, marginTop: 17}} />
  </div>
);

export const ChapterProgress: React.FC<{chapters: Chapter[]; activeIndex: number; surface?: 'dark' | 'photo'}> = ({chapters, activeIndex, surface = 'dark'}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 24}}>
    {chapters.map((chapter, i) => (
      <div key={`${i}-${chapter.label}`} style={{display: 'flex', alignItems: 'center', gap: 12, color: surface === 'photo' ? t.ink : i === activeIndex ? t.white : t.muted, opacity: i > activeIndex ? 0.58 : 1}}>
        <div style={{width: 38, height: 38, border: `1px solid ${i === activeIndex ? t.blue : surface === 'photo' ? 'rgba(8,18,36,.22)' : t.line}`, background: i === activeIndex ? t.blue : surface === 'photo' ? 'transparent' : 'rgba(8,18,36,0.38)', color: i === activeIndex ? t.white : undefined, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, borderRadius: 5}}>{String(i + 1).padStart(2, '0')}</div>
        <span style={{fontSize: 23, fontWeight: i === activeIndex ? 700 : 400}}>{chapter.shortLabel ?? chapter.label}</span>
      </div>
    ))}
  </div>
);

export const SceneHeader: React.FC<{chapters: Chapter[]; activeIndex: number; surface?: 'dark' | 'photo'}> = ({chapters, activeIndex, surface = 'dark'}) => (
  <div style={{position: 'absolute', left: t.safeX, right: t.safeX, top: 58, height: 58, display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
    <BrandMark />
    <ChapterProgress chapters={chapters} activeIndex={activeIndex} surface={surface} />
  </div>
);

export const Eyebrow: React.FC<{children: React.ReactNode; surface?: 'dark' | 'photo'}> = ({children, surface = 'dark'}) => (
  <div style={{fontSize: 21, fontWeight: 700, letterSpacing: 3.5, color: surface === 'photo' ? t.blue : t.cyan, display: 'flex', alignItems: 'center', gap: 13}}><span style={{width: 24, height: 2, background: t.blue}} />{children}</div>
);

export const KeyPointCard: React.FC<{point: KeyPoint; index: number; surface?: 'dark' | 'photo'}> = ({point, index, surface = 'dark'}) => {
  const frame = useCurrentFrame();
  return <div style={{display: 'flex', gap: 22, alignItems: 'flex-start', opacity: interpolate(frame, [point.cueFrame, point.cueFrame + 14], [0, 1], enter), translate: `${interpolate(frame, [point.cueFrame, point.cueFrame + 18], [-20, 0], enter)}px 0px`}}>
    <div style={{fontSize: 24, color: surface === 'photo' ? t.blue : t.cyan, width: 30, paddingTop: 9, fontVariantNumeric: 'tabular-nums'}}>{String(index + 1).padStart(2, '0')}</div>
    <div style={{borderLeft: `2px solid ${t.blue}`, paddingLeft: 24}}>
      <div style={{fontSize: 38, lineHeight: 1.5, fontWeight: 700}}>{point.title}</div>
      {point.detail ? <div style={{fontSize: 26, lineHeight: 1.5, marginTop: 7, color: surface === 'photo' ? t.photoMuted : t.muted}}>{point.detail}</div> : null}
    </div>
  </div>;
};

export const ComparisonBars: React.FC<{items: BarDatum[]; maxValue: number; unit: string}> = ({items, maxValue, unit}) => {
  const frame = useCurrentFrame();
  return <div style={{display: 'flex', flexDirection: 'column', gap: 34}}>
    {items.map((item, i) => {
      const color = item.color === 'gold' ? t.gold : t.blue;
      const value = interpolate(frame, [item.cueFrame, item.cueFrame + 34], [0, item.value], enter);
      return <div key={`${i}-${item.label}`} style={{display: 'grid', gridTemplateColumns: '272px 1fr 220px', alignItems: 'center', gap: 30, height: 84, opacity: interpolate(frame, [item.cueFrame, item.cueFrame + 10], [0, 1], enter)}}>
        <div style={{fontSize: 36, fontWeight: 700, color: item.color === 'gold' ? t.gold : t.white}}>{item.label}</div>
        <div style={{position: 'relative', height: 28, borderRadius: 3, background: 'rgba(168,180,199,0.1)', border: `1px solid ${t.line}`}}>
          <div style={{position: 'absolute', left: 0, top: -1, bottom: -1, width: `${Math.min(100, Math.max(0, value / maxValue * 100))}%`, background: `linear-gradient(90deg, ${color}80, ${color})`, borderRadius: 3, boxShadow: `0 0 30px ${color}20`}} />
          <div style={{position: 'absolute', left: `${Math.min(100, Math.max(0, value / maxValue * 100))}%`, top: 8, width: 10, height: 10, translate: '-5px 0', borderRadius: '50%', background: t.white, opacity: value > 0 ? 1 : 0}} />
        </div>
        <div style={{display: 'flex', gap: 10, alignItems: 'baseline', justifyContent: 'flex-end', fontVariantNumeric: 'tabular-nums', color: item.color === 'gold' ? t.gold : t.white}}><span style={{fontSize: 70, lineHeight: 1, fontWeight: 700, minWidth: 104, textAlign: 'right'}}>{Math.round(value)}</span><span style={{fontSize: 27, color: t.muted}}>{unit}</span></div>
      </div>;
    })}
  </div>;
};

export const StepList: React.FC<{steps: StepDatum[]}> = ({steps}) => {
  const frame = useCurrentFrame();
  return <div style={{display: 'flex', flexDirection: 'column', gap: 40}}>
    {steps.map((step, i) => {
      const active = frame >= step.cueFrame && (i === steps.length - 1 || frame < steps[i + 1].cueFrame);
      const complete = frame >= step.cueFrame;
      return <div key={`${i}-${step.label}`} style={{opacity: interpolate(frame, [step.cueFrame, step.cueFrame + 15], [0.25, 1], enter), borderLeft: `2px solid ${active ? t.blue : complete ? 'rgba(45,107,255,0.35)' : t.line}`, paddingLeft: 23}}>
        <div style={{fontSize: 22, color: active ? t.cyan : t.muted, letterSpacing: 2, marginBottom: 13}}>STEP {String(i + 1).padStart(2, '0')}</div>
        <div style={{fontSize: 38, fontWeight: 700, lineHeight: 1.4, color: active ? t.white : t.muted}}>{step.label}</div>
        <div style={{fontSize: 27, lineHeight: 1.5, marginTop: 9, color: t.muted}}>{step.detail}</div>
      </div>;
    })}
  </div>;
};

export const SubtleGrid: React.FC = () => (
  <div style={{position: 'absolute', inset: 0, backgroundImage: `linear-gradient(${t.line} 1px, transparent 1px),linear-gradient(90deg, ${t.line} 1px, transparent 1px)`, backgroundSize: '120px 120px', opacity: 0.12, maskImage: 'linear-gradient(90deg, transparent 0%, black 100%)'}} />
);
