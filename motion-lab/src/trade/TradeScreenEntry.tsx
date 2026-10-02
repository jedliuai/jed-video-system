import {Composition, registerRoot} from 'remotion';
import {TradeScreenOverlay} from './TradeScreenOverlay';
import '../fonts';

registerRoot(() => <Composition id="TradeScreen" component={TradeScreenOverlay} width={2560} height={1440} fps={30} durationInFrames={150} defaultProps={{durationInFrames: 150, title: '产品与成本', detail: '保留真实操作', step: '01', color: '#58B3ED'}} calculateMetadata={({props}) => ({durationInFrames: Number(props.durationInFrames)})} />);
