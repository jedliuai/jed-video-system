import React from 'react';
import {AbsoluteFill, Composition, Freeze, Img, registerRoot, staticFile} from 'remotion';
import {PlannedOverlay, type ProductionProps} from '../src/production/ProductionReel';
import '../src/fonts';

// Isolated candidates only. Production tokens and delivered drafts stay unchanged.
type ReviewProps = ProductionProps & {edgeMode: 'none' | 'fine'; sourceFrame: number; previewDirectory: string};

const AlphaCandidate: React.FC<ReviewProps> = (props) => <Freeze frame={props.sourceFrame}>
  <AbsoluteFill className={`clean-edge-${props.edgeMode}`}>
    <style>{`.clean-edge-${props.edgeMode} * {
      text-shadow: none !important;
      -webkit-text-stroke: ${props.edgeMode === 'fine' ? '.02em white' : '0 transparent'} !important;
      paint-order: stroke fill;
    }`}</style>
    <PlannedOverlay overlays={props.overlays} durationInFrames={props.durationInFrames} />
  </AbsoluteFill>
</Freeze>;

const Comparison: React.FC<ReviewProps> = (props) => <AbsoluteFill style={{background: '#f5f7fa', fontFamily: 'JedSans', color: '#102138'}}>
  {[{mode: 'none', name: 'A · 无白边', note: '推荐：保留原色，去掉白色光晕和描边'},
    {mode: 'fine', name: 'B · 极细白边', note: '保留一点边缘分离感，去掉白色光晕'}].map((item, i) => <div key={item.mode} style={{position: 'absolute', top: 0, left: i * 734, width: 730, height: 880}}>
      <div style={{height: 96, padding: '20px 28px', boxSizing: 'border-box', background: item.mode === 'none' ? '#e9efff' : '#f5f7fa'}}>
        <div style={{fontSize: 28, fontWeight: 700}}>{item.name}</div>
        <div style={{fontSize: 18, marginTop: 4, color: '#50617a'}}>{item.note}</div>
      </div>
      <div style={{position: 'relative', height: 740, overflow: 'hidden'}}>
        <Img src={staticFile(`${props.previewDirectory}/${item.mode}-composite.png`)} style={{position: 'absolute', width: 1920, height: 1080, left: -80, top: -205}} />
      </div>
      <div style={{padding: '10px 28px', fontSize: 17, color: '#50617a'}}>透明 MOV 解码合成候选 · 剪映显示尚未核对</div>
    </div>)}
</AbsoluteFill>;

const defaults: ReviewProps = {sourceSrc: 'live-source.mp4', durationInFrames: 1224, clips: [], overlays: [], captions: [], edgeMode: 'none', sourceFrame: 172, previewDirectory: 'reviews/clean-edge-20261002-r1'};
const ReviewRoot = () => <>
  <Composition id="CleanEdgeAlpha" component={AlphaCandidate} defaultProps={defaults} width={1920} height={1080} fps={30} durationInFrames={1224} />
  <Composition id="CleanEdgeComparison" component={Comparison} defaultProps={defaults} width={1468} height={880} fps={30} durationInFrames={1224} />
</>;
registerRoot(ReviewRoot);
