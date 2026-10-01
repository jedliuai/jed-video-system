export type Chapter = {label: string; shortLabel?: string};
export type KeyPoint = {title: string; detail?: string; cueFrame: number};
export type BarDatum = {label: string; value: number; color?: 'blue' | 'gold'; cueFrame: number};
export type StepDatum = {label: string; detail: string; cueFrame: number};

export type TalkingHeadContent = {
  background: string;
  chapters: Chapter[];
  chapterIndex: number;
  eyebrow: string;
  headline: string[];
  points: KeyPoint[];
  footer: string;
};
export type ComparisonContent = {
  chapters: Chapter[];
  chapterIndex: number;
  eyebrow: string;
  headline: string;
  subtitle: string;
  items: BarDatum[];
  maxValue: number;
  unit: string;
  takeaway: string;
  takeawayCue: number;
  disclosure: string;
};
export type TutorialContent = {
  background: string;
  chapters: Chapter[];
  chapterIndex: number;
  eyebrow: string;
  headline: string;
  steps: StepDatum[];
  note: string;
};

const chapters: Chapter[] = [
  {label: '建立观点', shortLabel: '观点'},
  {label: '数据比较', shortLabel: '比较'},
  {label: '实机演示', shortLabel: '演示'},
];

export const talkingHeadDefault: TalkingHeadContent = {
  background: 'talking-head.jpg',
  chapters,
  chapterIndex: 0,
  eyebrow: 'JED / AI CONTENT SYSTEM',
  headline: ['把复杂的事，', '讲得更清楚。'],
  points: [
    {title: '先保留人物的表达', detail: '观点跟随讲述，逐层出现', cueFrame: 30},
    {title: '再建立信息的层次', detail: '让重点留在画面里', cueFrame: 75},
  ],
  footer: '01 / 观点建立',
};

export const comparisonDefault: ComparisonContent = {
  chapters,
  chapterIndex: 1,
  eyebrow: 'JED / VISUAL EXPLAINER',
  headline: '让比较，一眼就看懂。',
  subtitle: '同一坐标 · 逐项建立 · 数字与图形同步',
  items: [
    {label: '原始表达', value: 28, color: 'blue', cueFrame: 20},
    {label: '结构整理', value: 46, color: 'blue', cueFrame: 40},
    {label: '视觉辅助', value: 72, color: 'blue', cueFrame: 60},
    {label: '完整呈现', value: 92, color: 'gold', cueFrame: 80},
  ],
  maxValue: 100,
  unit: '分',
  takeaway: '每一步，都让信息更清晰',
  takeawayCue: 130,
  disclosure: '示例数据 · 仅用于视觉预览',
};

export const tutorialDefault: TutorialContent = {
  background: 'screen-recording.jpg',
  chapters,
  chapterIndex: 2,
  eyebrow: 'JED / SCREEN WALKTHROUGH',
  headline: '跟着操作，看懂流程。',
  steps: [
    {label: '先看全局', detail: '确认当前界面', cueFrame: 10},
    {label: '找到重点', detail: '跟随讲述定位', cueFrame: 60},
    {label: '完成操作', detail: '保留完整路径', cueFrame: 110},
  ],
  note: '录屏阶段 · 保留操作画面',
};
