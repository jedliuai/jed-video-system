import React from 'react';
import {AbsoluteFill, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ProductionReel, type ProductionProps} from '../production/ProductionReel';

export type ChapterEvent = {id: string; number: string; title: string; outputStartFrame: number; durationInFrames: number; artSrc: string};
export type ChapterProps = ProductionProps & {chapterTransitions: ChapterEvent[]};

const ChapterCard: React.FC<{event: ChapterEvent}> = ({event}) => {
  const frame = useCurrentFrame();
  const end = event.durationInFrames;
  const opacity = interpolate(frame, [0, 5, end - 7, end - 1], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const enter = interpolate(frame, [2, 8], [0, 1], {easing: Easing.out(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const scale = interpolate(frame, [0, end - 1], [1, 1.012]);
  return <AbsoluteFill style={{opacity, backgroundColor: '#F7F5EF', color: '#102138', fontFamily: 'JedSans'}}>
    <Img src={staticFile(event.artSrc)} style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}} />
    <div style={{position: 'absolute', top: 82, left: 112, fontSize: 30, fontWeight: 700}}>Jed<span style={{color: '#376BFA'}}> .</span></div>
    <div style={{position: 'absolute', left: 144, top: 285, width: 990, opacity: enter, transform: `translateY(${(1 - enter) * 16}px)`}}>
      <div style={{fontSize: 78, lineHeight: 1, fontWeight: 700, color: '#376BFA', letterSpacing: '-3px'}}>{event.number}</div>
      <div style={{width: 68, height: 4, backgroundColor: '#376BFA', marginTop: 32, marginBottom: 38}} />
      <div style={{fontSize: 110, lineHeight: 1.2, fontWeight: 700, letterSpacing: '-2px'}}>{event.title}</div>
    </div>
  </AbsoluteFill>;
};

/** Cover the spoken bridge without shifting, muting or cutting source audio. */
export const ChapterTransitionPreview: React.FC<ChapterProps> = (props) => <AbsoluteFill>
  <ProductionReel {...props} />
  {props.chapterTransitions.map(event => <Sequence key={event.id} from={event.outputStartFrame} durationInFrames={event.durationInFrames}><ChapterCard event={event} /></Sequence>)}
</AbsoluteFill>;
