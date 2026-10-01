# 从静帧样式到真实口播动效

用户已选 A 布局，并明确要求直接在原画面上呈现元素，不加深色底、渐变遮罩或面板。`config/visual-preferences.json` 保存这一决定。

## 三种输出共用一套动效

- `motion-lab/src/live/TalkingHeadOverlay.tsx`：只包含文字、序号、细线、章节标记；没有底片、音轨或铺满画面的色层。它适合输出带 Alpha 的独立动效资产。
- `motion-lab/src/visual-a/TalkingHeadScene.tsx`：静帧底片与同一 Overlay 组合，保留第一阶段样片的 API 和已选外观。
- `motion-lab/src/live/LiveTalkingHeadScene.tsx`：真实视频底片与同一 Overlay 组合。保留素材自带的人声与音效，播放速率为 1，不循环静帧。

媒体与内容分开后，换原片、调整文案、改出现时机和选择导出格式，不需要各写一套视觉场景。根组件负责注册 Composition、总时长和导出参数，场景模块不启动渲染服务。

## 传入内容和时间

`TalkingHeadOverlayContent` 是原 `TalkingHeadContent` 去掉 `background` 后的类型；原内容对象也可以继续传入。

标题仍是 `headline` 行数组，要点仍是 `points` 数组，每个要点的 `cueFrame` 是相对于该动效层起点的帧号。可选 `headlineCueFrame` 调整标题起点，默认 4；`showHeader` 和 `showFooter` 默认开启，遇到原片已有品牌标记或章节信息时可关闭，以免重复。

真实视频场景额外要求 `source`：

| 字段 | 含义 |
| --- | --- |
| `src` | `motion-lab/public/` 内相对路径或 HTTP(S) URL |
| `trimBeforeFrames` | 剪去原片开头多少帧，非负整数 |
| `durationInFrames` | 取多少帧，正整数，与该场景 Composition 总时长对应 |

以上时间都按 **Composition 的 FPS** 计算。例如 30 fps 场景中，素材从 5 秒开始取 8 秒，应传入 150 和 240，不能按原片可能存在的 60 fps 直接相乘。文案 cue 也要从剪段起点重新计算。`volume` 默认 1，使用原片嵌入音频，不额外叠一份口播音轨。

本项目固定 Remotion 4.0.530，使用该版本已有的 `OffthreadVideo`。它在导出时由浏览器外的 FFmpeg 解码精确帧，在 Studio 中使用视频元素播放；`trimBefore`、`durationInFrames` 和嵌入音频由官方组件处理。参见 [Remotion OffthreadVideo 官方文档](https://www.remotion.dev/docs/offthreadvideo)。当前没有安装 `@remotion/media`，因此没有为这次增量引入另一套媒体依赖。

## 透明度探针

`AlphaProbeScene` 是 1920×1080、30 fps 下使用的 90 帧探针，包含不透明文字、增长的蓝线、半透明蓝色方块和金色圆。根组件可以将同一场景导出成 PNG、ProRes 4444 MOV 和 WebM Alpha，再分别解码核验。

在第 35 帧之后：

- 四角应保持 Alpha 0。
- 点 `(150, 650)` 位于半透明蓝块内，Alpha 约 128。
- 点 `(344, 684)` 位于不透明金圆内，Alpha 应为 255。

容器不设置背景，避免错误导出整张不透明底色；但透明资产仍必须使用支持 Alpha 的编码和导出参数。格式兼容性、剪映导入效果由实际导出和编辑器探针验证，不能只根据文件后缀或像素格式声明认定成功。

## 安全区和当前边界

保留已审核的 1920×1080 布局：正文主要放在左侧 x=112～782；主标题 y=225 起；页脚距离下边 120；原片人物脸与底部已烧录字幕优先保留。没有额外重复字幕或人物小窗。原片已有侧栏宣传字、字幕和角标，是否关闭章节头和页脚需要结合每段原片检查。

当前布局基于已审核画面，还没有自动人脸检测与动态避让。更换人物位置、镜头比例或长文案后，需要重新检查画面；不把这套左侧布局宣称为适配所有口播的自动模板。录屏片段默认不添加 B-roll，口播动效层也没有下载或生成 B-roll 的副作用。

本阶段代码检查：`npm run lint` 通过（ESLint 与 TypeScript）。透明度、口播声音和逐帧视效以根流程实际渲染结果为准。
