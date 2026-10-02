import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';

export type TradeScreenProps = {durationInFrames: number; title: string; detail?: string; step: string; color: string; box?: [number, number, number, number]; choices?: string[]};

/** The caption badge lives in the recording's existing upper margin, outside the UI. */
export const TradeScreenOverlay: React.FC<TradeScreenProps> = ({durationInFrames, title, detail = '', step, color, box, choices = []}) => {
  const frame = useCurrentFrame();
  const easing = {easing: Easing.out(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const enter = interpolate(frame, [0, 10], [0, 1], easing);
  const leave = interpolate(frame, [Math.max(11, durationInFrames - 10), durationInFrames - 1], [1, 0], easing);
  const [x, y, width, height] = box ?? [0, 0, 0, 0];
  const c = Math.min(28, Math.min(width, height) / 3);
  const brackets = `M${x + c} ${y}H${x}V${y + c} M${x + width - c} ${y}H${x + width}V${y + c} M${x} ${y + height - c}V${y + height}H${x + c} M${x + width - c} ${y + height}H${x + width}V${y + height - c}`;
  return <AbsoluteFill style={{backgroundColor: 'transparent', opacity: enter * leave, fontFamily: 'JedSans, sans-serif', textShadow: 'none', WebkitTextStroke: '0 transparent'}}>
    <div style={{position: 'absolute', left: 66, top: 15, height: 58, display: 'flex', alignItems: 'center', gap: 17, border: `2px solid ${color}`, borderRadius: 12, padding: '0 20px', boxSizing: 'border-box', color: '#FFFFFF'}}>
      <span style={{fontSize: 22, fontWeight: 700, color}}>{step}</span>
      <span style={{fontSize: 30, fontWeight: 700}}>{title}</span>
      {detail ? <span style={{fontSize: 22, color: '#DCE7F3'}}>{detail}</span> : null}
      {choices.map((choice, i) => <span key={choice} style={{borderLeft: `2px solid ${['#58B3ED', '#58C1B9', '#E3BD67', '#BA9BF1'][i % 4]}`, paddingLeft: 12, color: ['#58B3ED', '#58C1B9', '#E3BD67', '#BA9BF1'][i % 4], fontSize: 22, fontWeight: 700}}>{choice}</span>)}
    </div>
    {box ? <svg width={2560} height={1440} viewBox="0 0 2560 1440"><path d={brackets} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" /></svg> : null}
  </AbsoluteFill>;
};
