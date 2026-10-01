# Jed Motion Lab

Remotion 4.0.530 视觉原型，使用本地字体与用户素材采样帧。

- src/visual-a/tokens.ts：品牌颜色、字体与保护区。
- src/visual-a/content.ts：三种场景的内容与动画落点。
- src/visual-a/components.tsx：章节导航、观点、图表与步骤列表。
- src/visual-a/*Scene.tsx：口播、比较和教程场景。
- src/visual-b/：另一种口播版式，标记设计来源。
- src/StyleReel.tsx：三段各 6 秒的样式展示。

安装：npm ci。检查：npm run lint。预览：npx remotion studio --no-open。

项目根 scripts/prepare-preview.ps1 与 scripts/render-preview.ps1 负责本机素材准备和导出。此处不包含转录、B-roll 下载或剪映草稿写入。
