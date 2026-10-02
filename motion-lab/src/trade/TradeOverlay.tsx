import React, {type CSSProperties} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {jedTokens as t} from '../visual-a/tokens';

const palette = {blue: '#2D6BFF', teal: '#087D88', gold: '#A76D0B', violet: '#7250BE'};
const ease = {easing: Easing.out(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const colors = Object.values(palette);
const colorFor = (value: string, index: number) => palette[value as keyof typeof palette] ?? value ?? colors[index % colors.length];

export type TradeOverlayProps = {
  durationInFrames: number;
  kind: 'pricing-flow' | 'ai-build' | 'audience' | 'source-cta';
  heading: string;
  /** pricing-flow: cost, profit, refund, expenses, quote; other layouts: up to four steps or two roles. */
  nodes: {label: string; detail: string; color: string; cue: number}[];
  conclusion: string;
  conclusionCue: number;
};

/** Transparent 1920×1080 design coordinates. Render within a uniformly scaled native canvas. */
export const TradeOverlay: React.FC<TradeOverlayProps> = ({durationInFrames, kind, heading, nodes, conclusion, conclusionCue}) => {
  const frame = useCurrentFrame();
  const reveal = (cue: number, length = 12) => interpolate(frame, [cue, cue + length], [0, 1], ease);
  const enter = (cue: number): CSSProperties => ({opacity: reveal(cue), transform: `translateY(${8 * (1 - reveal(cue))}px)`});
  const exitStart = Math.max(0, durationInFrames - 10);
  const exit = interpolate(frame, [exitStart, Math.max(exitStart + 1, durationInFrames - 1)], [0, 1], ease);
  const color = (index: number) => colorFor(nodes[index]?.color || colors[index % colors.length], index);
  const renderText = (index: number, titleSize = 36, centered = false) => {
    const node = nodes[index];
    if (!node) return null;
    return <div style={{textAlign: centered ? 'center' : 'left', ...enter(node.cue)}}>
      <div style={{fontSize: titleSize, fontWeight: 700, lineHeight: 1.2, color: color(index), whiteSpace: 'pre-line'}}>{node.label}</div>
      {node.detail ? <div style={{marginTop: 9, fontSize: 25, lineHeight: 1.3, color: t.photoMuted, whiteSpace: 'pre-line'}}>{node.detail}</div> : null}
    </div>;
  };
  const verticalArrow = (key: string, x: number, y1: number, y2: number, cue: number, arrowColor: string) => (
    <g key={key} opacity={reveal(cue)}>
      <path d={`M${x} ${y1}V${y2 - 7}`} fill="none" stroke={arrowColor} strokeWidth={3} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - reveal(cue, 15)} />
      {/* Tip overlaps the shaft. No separate alpha seam or white stroke. */}
      <path d={`M${x} ${y2}l-6 -10h12Z`} fill={arrowColor} stroke="none" opacity={reveal(cue + 10, 5)} />
    </g>
  );

  return <AbsoluteFill style={{backgroundColor: 'transparent', pointerEvents: 'none', fontFamily: t.font, color: t.ink, opacity: 1 - exit, textShadow: 'none', WebkitTextStroke: '0 transparent'}}>
    <div style={{position: 'absolute', left: 95, top: 220, width: 650, fontSize: kind === 'source-cta' ? 54 : 47, fontWeight: 700, lineHeight: 1.16, letterSpacing: -0.8, whiteSpace: 'pre-line', ...enter(0)}}>{heading}</div>

    {kind === 'pricing-flow' ? <>
      <div style={{position: 'absolute', left: 135, top: 352, width: 570}}>{renderText(0, 37, true)}</div>
      <svg width={650} height={355} viewBox="0 0 650 355" stroke="none" style={{position: 'absolute', left: 95, top: 412}} aria-hidden>
        {[1, 2, 3].map((index) => {
          const x = 105 + (index - 1) * 220;
          const cue = nodes[index]?.cue ?? 0;
          const outputCue = nodes[4]?.cue ?? cue + 24;
          return <g key={`pricing-branch-${index}`}>
            <path d={`M325 0V24H${x}V60`} fill="none" stroke={color(index)} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - reveal(cue, 16)} opacity={reveal(cue)} />
            <circle cx={x} cy={60} r={4} fill={color(index)} stroke="none" opacity={reveal(cue + 10)} />
            <path d={`M${x} 206V230H325V242`} fill="none" stroke={color(index)} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - reveal(outputCue, 18)} opacity={reveal(outputCue)} />
          </g>;
        })}
        <path d="M325 248l-7 -12h14Z" fill={color(4)} stroke="none" opacity={reveal((nodes[4]?.cue ?? 0) + 13, 5)} />
      </svg>
      {[1, 2, 3].map((index) => <div key={`pricing-variable-${index}`} style={{position: 'absolute', left: 95 + (index - 1) * 220, top: 493, width: 210}}>{renderText(index, 28, true)}</div>)}
      <div style={{position: 'absolute', left: 120, top: 687, width: 600}}>{renderText(4, 40, true)}</div>
    </> : null}

    {kind === 'ai-build' ? <>
      <svg width={34} height={429} viewBox="0 0 34 429" stroke="none" style={{position: 'absolute', left: 95, top: 355}} aria-hidden>
        {nodes.slice(1, 4).map((node, index) => verticalArrow(`build-link-${index}`, 13, index * 110 + 44, (index + 1) * 110 + 8, node.cue, color(index + 1)))}
      </svg>
      {nodes.slice(0, 4).map((node, index) => <div key={`build-stage-${index}`} style={{position: 'absolute', left: 95, top: 355 + index * 110, width: 650}}>
        <svg width={28} height={32} viewBox="0 0 28 32" stroke="none" style={{position: 'absolute', left: 0, top: 5, opacity: reveal(node.cue)}} aria-hidden><circle cx={13} cy={16} r={8} fill={color(index)} stroke="none" /></svg>
        <div style={{marginLeft: 48}}>{renderText(index, 34)}</div>
      </div>)}
    </> : null}

    {kind === 'audience' ? <>
      <div style={{position: 'absolute', left: 95, top: 408, width: 292}}>{renderText(0, 39)}</div>
      <div style={{position: 'absolute', left: 441, top: 408, width: 304}}>{renderText(1, 39)}</div>
      <svg width={650} height={148} viewBox="0 0 650 148" stroke="none" style={{position: 'absolute', left: 95, top: 566}} aria-hidden>
        {[0, 1].map((index) => <path key={`audience-union-${index}`} d={`M${index === 0 ? 105 : 495} 0V43Q${index === 0 ? 105 : 495} 64 325 64V91`} fill="none" stroke={color(index)} strokeWidth={2.5} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - reveal(conclusionCue, 20)} opacity={reveal(conclusionCue)} />)}
        <path d="M325 99l-7 -12h14Z" fill={palette.gold} stroke="none" opacity={reveal(conclusionCue + 15, 5)} />
      </svg>
      <div style={{position: 'absolute', left: 110, top: 697, width: 620, fontSize: 32, fontWeight: 700, lineHeight: 1.2, textAlign: 'center', whiteSpace: 'pre-line', color: palette.gold, ...enter(conclusionCue)}}>{conclusion}</div>
    </> : null}

    {kind === 'source-cta' ? <>
      {nodes.slice(0, 2).map((node, index) => <div key={`source-action-${index}`} style={{position: 'absolute', left: 95, top: 421 + index * 148, width: 650}}>
        <div style={{position: 'absolute', left: 0, top: 8, width: 5, height: 54, backgroundColor: color(index), opacity: reveal(node.cue)}} />
        <div style={{marginLeft: 26}}>{renderText(index, 42)}</div>
      </div>)}
      <svg width={38} height={75} viewBox="0 0 38 75" stroke="none" style={{position: 'absolute', left: 96, top: 492}} aria-hidden>{verticalArrow('source-next', 13, 0, 65, nodes[1]?.cue ?? 0, color(1))}</svg>
    </> : null}

    {kind !== 'audience' && conclusion ? <div style={{position: 'absolute', left: 95, top: 793, width: 650, fontSize: 29, fontWeight: 700, lineHeight: 1.18, whiteSpace: 'pre-line', color: palette.gold, ...enter(conclusionCue)}}>{conclusion}</div> : null}
  </AbsoluteFill>;
};
