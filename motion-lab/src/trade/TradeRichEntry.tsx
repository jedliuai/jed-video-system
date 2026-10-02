import React from 'react';
import {Composition,registerRoot} from 'remotion';
import {TradeRichOverlay,type TradeRichProps} from './TradeRichOverlay';
import '../fonts';
const Native:React.FC<TradeRichProps>=(props)=><div style={{position:'absolute',width:1920,height:1080,transform:'scale(1.3333333333333333)',transformOrigin:'top left'}}><TradeRichOverlay {...props}/></div>;
const defaults:TradeRichProps={durationInFrames:240,kind:'excel-pain',eyebrow:'01 / 报价的起点',heading:'从 Excel 反复算\n到工作台直接报',nodes:[{label:'工厂给成本',detail:'税价与产品资料',cue:0,color:'blue',icon:'sheet'},{label:'业务员报客户',detail:'利润与出口费用',cue:30,color:'teal',icon:'person'},{label:'统一计算',cue:60,color:'gold'}],conclusion:'让重复计算，变成一次录入',conclusionCue:90};
registerRoot(()=> <Composition id="TradeRich" component={Native} width={2560} height={1440} fps={30} durationInFrames={240} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:Number(props.durationInFrames)})}/>);
