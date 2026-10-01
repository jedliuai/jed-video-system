import {TransitionSeries} from '@remotion/transitions';
import {ComparisonScene, TalkingHeadScene, TutorialScene} from './visual-a';

export const StyleReel = () => (
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={180} name="TalkingHeadA"><TalkingHeadScene /></TransitionSeries.Sequence>
    <TransitionSeries.Sequence durationInFrames={180} name="ComparisonA"><ComparisonScene /></TransitionSeries.Sequence>
    <TransitionSeries.Sequence durationInFrames={180} name="TutorialA"><TutorialScene /></TransitionSeries.Sequence>
  </TransitionSeries>
);
