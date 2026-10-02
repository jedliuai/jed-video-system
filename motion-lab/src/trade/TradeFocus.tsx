import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';

export type TradeFocusProps = {durationInFrames:number; box:[number,number,number,number]; color:string};
/** Four corner brackets leave the original field, numbers and face readable. */
export const TradeFocus: React.FC<TradeFocusProps> = ({durationInFrames,box,color}) => {
  const f=useCurrentFrame();
  const reveal=interpolate(f,[0,8],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.out(Easing.cubic)});
  const leave=interpolate(f,[durationInFrames-9,durationInFrames-1],[1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const [x,y,w,h]=box;
  const l=Math.min(28,w/4,h/3);
  const d=`M${x} ${y+l}V${y}H${x+l} M${x+w-l} ${y}H${x+w}V${y+l} M${x+w} ${y+h-l}V${y+h}H${x+w-l} M${x+l} ${y+h}H${x}V${y+h-l}`;
  return <AbsoluteFill style={{backgroundColor:'transparent',opacity:reveal*leave}}><svg width={2560} height={1440} viewBox="0 0 2560 1440"><path d={d} fill="none" stroke={color} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" /></svg></AbsoluteFill>;
};
