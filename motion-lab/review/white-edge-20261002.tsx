import React from 'react';
import {AbsoluteFill, Composition, Freeze, registerRoot} from 'remotion';
import {ProductionReel, PlannedOverlay, type ProductionProps} from '../src/production/ProductionReel';
import '../src/fonts';

type ReviewProps = ProductionProps & {blurPx: number; sourceFrame: number};

const Frame: React.FC<ReviewProps> = (props) => <Freeze frame={props.sourceFrame}>
  <ProductionReel {...props} overlays={[]} />
  <AbsoluteFill className={`halo-candidate-${props.blurPx}`}>
    <style>{`.halo-candidate-${props.blurPx} * {text-shadow: 0 1px ${props.blurPx}px rgba(255,255,255,.65) !important;}`}</style>
    <PlannedOverlay overlays={props.overlays} durationInFrames={props.durationInFrames} />
  </AbsoluteFill>
</Freeze>;

const Comparison: React.FC<ReviewProps> = (props) => <AbsoluteFill style={{background: '#f5f7fa', fontFamily: 'JedSans', color: '#102138'}}>
  {[{name: 'A · 当前', blur: 4, note: '保留原厚度'}, {name: 'B · 稍薄', blur: 3, note: '推荐：收窄一档'}, {name: 'C · 更薄', blur: 2, note: '白边更轻'}].map((item, i) => <div key={item.name} style={{position: 'absolute', top: 0, left: i*734, width: 730, height: 880}}>
    <div style={{height: 96, padding: '20px 28px', boxSizing: 'border-box', background: item.blur === 3 ? '#e9efff' : '#f5f7fa'}}>
      <div style={{fontSize: 28, fontWeight: 700}}>{item.name}</div>
      <div style={{fontSize: 19, marginTop: 4, color: '#50617a'}}>{item.note}</div>
    </div>
    <div style={{position: 'relative', height: 740, overflow: 'hidden'}}>
      <div style={{position: 'absolute', width: 1920, height: 1080, left: -80, top: -205}}>
        <Frame {...props} blurPx={item.blur} />
      </div>
    </div>
    <div style={{padding: '10px 28px', fontSize: 17, color: '#50617a'}}>相同画面、字体和颜色 · 只调整白色光晕宽度</div>
  </div>)}
</AbsoluteFill>;

const defaults: ReviewProps = {sourceSrc: 'live-source.mp4', durationInFrames: 1224, clips: [], overlays: [], captions: [], blurPx: 3, sourceFrame: 180};
const ReviewRoot = () => <>
  <Composition id="WhiteEdgeFrame" component={Frame} defaultProps={defaults} width={1920} height={1080} fps={30} durationInFrames={1224} />
  <Composition id="WhiteEdgeComparison" component={Comparison} defaultProps={defaults} width={2202} height={880} fps={30} durationInFrames={1224} />
</>;

registerRoot(ReviewRoot);
