import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {jedTokens as t} from '../visual-a/tokens';

/** 90-frame probe at 30 fps: clear corners, opaque lettering, half-alpha patch. */
export const AlphaProbeScene: React.FC = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{fontFamily: t.font, color: t.blue}}>
    <div style={{position: 'absolute', left: 112, top: 225, fontSize: 100, fontWeight: 700}}>Jed / Alpha</div>
    <div style={{position: 'absolute', left: 112, top: 370, fontSize: 42, color: t.ink}}>透明文字 · 独立动效层</div>
    <div style={{position: 'absolute', left: 112, top: 470, width: interpolate(frame, [0, 35], [24, 580], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), height: 8, background: t.blue}} />
    <div style={{position: 'absolute', left: 112, top: 620, width: 128, height: 128, background: 'rgba(45,107,255,0.5)'}} />
    <div style={{position: 'absolute', left: 280, top: 620, width: 128, height: 128, background: t.gold, borderRadius: '50%', translate: `0px ${interpolate(frame, [0, 35], [20, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}px`}} />
  </AbsoluteFill>;
};
