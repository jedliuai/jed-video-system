export type EditorialTalkingHeadContent = {
  background: string;
  eyebrow: string;
  headline: string[];
  points: { title: string; detail?: string; cueFrame: number }[];
  footer: string;
};

// Structurally compatible with TalkingHeadContent, without depending on visual-a.
// Root can pass one content object to both visual implementations.
export const editorialTalkingHeadDefault: EditorialTalkingHeadContent = {
  background: "talking-head.jpg",
  eyebrow: "JED / AI CONTENT SYSTEM",
  headline: ["把复杂的事，", "讲得更清楚。"],
  points: [
    {
      title: "先保留人物的表达",
      detail: "观点跟随讲述，逐层出现",
      cueFrame: 30,
    },
    { title: "再建立信息的层次", detail: "让重点留在画面里", cueFrame: 75 },
  ],
  footer: "01 / 观点建立",
};
