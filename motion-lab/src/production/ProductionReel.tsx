import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {TalkingHeadOverlay, type TalkingHeadOverlayContent} from '../live';

export type PlannedClip = {id: string; sourceStartFrame: number; outputStartFrame: number; durationInFrames: number};
export type PlannedOverlay = {id: string; outputStartFrame: number; durationInFrames: number; headlineCueFrame: number; content: TalkingHeadOverlayContent};
export type PlannedCaption = {startFrame: number; endFrame: number; text: string};
export type ProductionProps = {
  sourceSrc: string;
  durationInFrames: number;
  clips: PlannedClip[];
  overlays: PlannedOverlay[];
  captions: PlannedCaption[];
};

const OverlayWindow: React.FC<{event: PlannedOverlay}> = ({event}) => {
  const frame = useCurrentFrame();
  const endFade = Math.min(10, event.durationInFrames - 1);
  const opacity = interpolate(frame, [event.durationInFrames - endFade - 1, event.durationInFrames - 1], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity}}><TalkingHeadOverlay content={event.content} headlineCueFrame={event.headlineCueFrame} /></AbsoluteFill>;
};

/** The exact same events render both a preview and the isolated alpha asset. */
export const PlannedOverlay: React.FC<{overlays: PlannedOverlay[]; durationInFrames: number}> = ({overlays}) => <>
  {overlays.map(event => <Sequence key={event.id} from={event.outputStartFrame} durationInFrames={event.durationInFrames}><OverlayWindow event={event} /></Sequence>)}
</>;

const CaptionLayer: React.FC<{captions: PlannedCaption[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const caption = captions.find(item => frame >= item.startFrame && frame < item.endFrame);
  if (!caption) return null;
  return <div style={{position: 'absolute', left: 190, right: 190, bottom: 88, textAlign: 'center', fontFamily: 'JedSans', fontSize: 40, fontWeight: 700, lineHeight: 1.5, color: '#fff', WebkitTextStroke: '1px #081224', textShadow: '0 2px 3px rgba(0,0,0,.8)', paintOrder: 'stroke fill'}}>{caption.text}</div>;
};

export const ProductionReel: React.FC<ProductionProps> = (props) => <AbsoluteFill>
  {props.clips.map(clip => <Sequence key={clip.id} from={clip.outputStartFrame} durationInFrames={clip.durationInFrames}>
    <OffthreadVideo src={staticFile(props.sourceSrc)} trimBefore={clip.sourceStartFrame} durationInFrames={clip.durationInFrames} volume={1} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
  </Sequence>)}
  <PlannedOverlay overlays={props.overlays} durationInFrames={props.durationInFrames} />
  <CaptionLayer captions={props.captions} />
</AbsoluteFill>;

export const productionDefaults: ProductionProps = {
  sourceSrc: 'live-source.mp4', durationInFrames: 1224,
  clips: [{id: 'main', sourceStartFrame: 0, outputStartFrame: 0, durationInFrames: 1224}],
  overlays: [], captions: [],
};
