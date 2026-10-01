import {Composition, Folder} from 'remotion';
import {ComparisonScene, TalkingHeadScene, TutorialScene} from './visual-a';
import {CodexFallbackTalkingHeadScene} from './visual-b/CodexFallbackTalkingHeadScene';
import {AgyTalkingHeadScene} from './visual-b/AgyTalkingHeadScene';
import {StyleReel} from './StyleReel';
import {AlphaProbeScene} from './live';
import {PlannedOverlay, ProductionReel, productionDefaults} from './production/ProductionReel';
import './fonts';
import {ChapterTransitionPreview} from './chapters/ChapterTransition';

export const RemotionRoot = () => (
  <>
    <Composition id="JedStyleReel" component={StyleReel} width={1920} height={1080} fps={30} durationInFrames={540} />
    <Composition id="AlphaProbe" component={AlphaProbeScene} width={1920} height={1080} fps={30} durationInFrames={90} />
    <Composition id="ProductionPreview" component={ProductionReel} defaultProps={productionDefaults} calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} width={1920} height={1080} fps={30} durationInFrames={1224} />
    <Composition id="ChapterTransitionPreview" component={ChapterTransitionPreview} defaultProps={{...productionDefaults, chapterTransitions: []}} calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} width={1920} height={1080} fps={30} durationInFrames={1224} />
    <Composition id="ChapterTransitionAsset" component={ChapterTransitionPreview} defaultProps={{...productionDefaults, clips: [], overlays: [], captions: [], chapterTransitions: []}} calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} width={1920} height={1080} fps={30} durationInFrames={54} />
    <Composition id="ProductionOverlay" component={PlannedOverlay} defaultProps={{overlays: [], durationInFrames: 348}} calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames})} width={1920} height={1080} fps={30} durationInFrames={348} />
    <Folder name="Jed-Style-Samples">
      <Composition id="TalkingHeadA" component={TalkingHeadScene} width={1920} height={1080} fps={30} durationInFrames={180} />
      <Composition id="ComparisonA" component={ComparisonScene} width={1920} height={1080} fps={30} durationInFrames={180} />
      <Composition id="TutorialA" component={TutorialScene} width={1920} height={1080} fps={30} durationInFrames={180} />
      <Composition id="TalkingHeadB" component={AgyTalkingHeadScene} width={1920} height={1080} fps={30} durationInFrames={180} />
      <Composition id="TalkingHeadFallback" component={CodexFallbackTalkingHeadScene} width={1920} height={1080} fps={30} durationInFrames={180} />
    </Folder>
  </>
);
