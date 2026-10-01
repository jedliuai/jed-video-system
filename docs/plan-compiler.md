# 原片时间到动效帧的唯一编译器

2026-10-01。`src/jed_plan/` 是一个无第三方依赖的时间编译器，只处理已经写好的人工计划。它不推断客户回答、不跑 ASR、不下载 B-roll，也不进行剪映写入或视频渲染。

## 输入与输出

入口 `plugins/jed-video-system/scripts/compile_plan.py` 接受 `--plan`、`--transcript`、`--output` 三个路径。输入计划结构见 `schemas/edit-plan.schema.json`；同一文件的 `$defs/renderProps` 描述编译后传给 Remotion 的结构。

计划保留源秒数、clips、overlays 与人工字幕；编译结果输出 sourceSrc、fps、总帧数、每个 clip 的源起始帧和输出起始帧、每个 overlay 的输出范围与局部 cueFrame、字幕输出区间和 timingReview。输入对象不会被修改。

正常预览与独立动效都消费同一编译结果。不能在 UI、FFmpeg 与 React 组件里分别再推算一套秒数映射。

## 时钟约定

当前仅接受整数 30 或 60 fps，以及 speed=1。变速会直接拒绝，因为时长、声画边界和字幕都需要完整的重映射实现，不能只改变视频播放速度。

每个源边界独立使用 Decimal 和 ROUND_HALF_UP 换算成帧，区间时长等于“末边界帧减首边界帧”。每个 clip 的输出起点等于此前 clip 帧时长之和；事件输出帧等于 clip 输出起点加事件源边界帧减 clip 源起点帧。这样共享边界总是得到同一个帧，避免分别四舍五入时长后累积漂移。

overlay 的 headlineCueFrame 与 points[].cueFrame 都是该 overlay 内的局部帧。timingReview 同时保存局部帧和最终输出帧。30 fps 单边界最大量化误差为约 16.7 ms，60 fps 为约 8.3 ms；这不包括模型对齐误差。不要把帧量化当成 ASR 已经逐帧验收。

## 校验规则

- plan.transcriptSourceSha256 必须等于实际转录输入的 SHA256，不以路径名代替身份核对。
- 秒数必须有限，源区间合法，clips 不能越界或相互重叠，ID 不能重复。
- overlay 完全属于一个指定 clip；headline 和要点的 wordId 必须存在，且完整位于该 overlay 的源窗口里。
- clips 的声画切点不能位于任一转录词内部。overlay 的退场只是视觉层结束，允许在词内部，不能把它误当音频剪切。
- 字幕与各个保留 clip 求交，再分别映射。跨越删除区间的同一条字幕会保留在两边，不会因“没有完整落在一段里”而被整条丢掉。短到量化后没有展示帧的保留字幕区间会报错。
- 保留 approximateBoundary、timingQuality 和人工试听状态供后续抽查。插值边界不会因为编译成整数帧而变成可靠边界。

## 本次案例

root 的 40.8 秒 live-source.mp4 使用一段 speed=1 的 clip，不裁掉原人声。按 30 fps 编译应为 1224 帧。两个口播信息层分别为 0–6.8 秒和 6.8–11.6 秒，之后保留教程录屏；B-roll 决策仍来自已确认的客户偏好，编译器不会额外推荐或创建它。

live-source 的画面可来自另一份经过独立核验的无包装源片，但其 transcriptSourceSha256 仍引用真正跑过 ASR 的案例文件。音频一致性与原素材 offset 必须在独立 manifest 里证明；这里只保证使用了指定转录的时钟，不能替代源片映射验收。

## 测试

`tests/plan_compiler_test.py` 覆盖两段裁切后的 cue、跨裁切字幕拆分、错哈希、未知 anchor、词内部 cut、视觉退场、变速拒绝、源重叠、事件越界、anchor 越界、非有限秒数、half-up 与端点相减、30/60 fps 误差，以及输入不变。当前 13 项通过。CLI 用原子替换写输出，失败使用非零退出码，不写伪成功结果。
