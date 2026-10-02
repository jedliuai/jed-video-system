import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {TradeOverlay, type TradeOverlayProps} from './TradeOverlay';
import '../fonts';
import {TradeFocus} from './TradeFocus';

/** Native rendering: scale geometry before rasterization, never resize finished overlays. */
const NativeTradeOverlay: React.FC<TradeOverlayProps> = (props) => <div style={{position: 'absolute', width: 1920, height: 1080, transform: 'scale(1.3333333333333333)', transformOrigin: 'top left'}}><TradeOverlay {...props} /></div>;

const defaults: TradeOverlayProps = {durationInFrames: 180, kind: 'pricing-flow', heading: '工厂成本，变成\n客户报价', nodes: [], conclusion: '', conclusionCue: 0};
registerRoot(() => <>
  <Composition id="TradeReview" component={NativeTradeOverlay} width={2560} height={1440} fps={30} durationInFrames={180} defaultProps={defaults} calculateMetadata={({props}) => ({durationInFrames: Number(props.durationInFrames)})} />
  <Composition id="TradeFocus" component={TradeFocus} width={2560} height={1440} fps={30} durationInFrames={90} defaultProps={{durationInFrames:90,box:[100,100,600,200] as [number,number,number,number],color:'#087D88'}} calculateMetadata={({props})=>({durationInFrames:Number(props.durationInFrames)})}/>
</>);
