# 已确认章节配方的本机交接

本文记录0.5连续原声cover交接。用户随后改为独立章节停顿与短音效，0.6新预览和时间映射见 [chapter-insertion.md](chapter-insertion.md)。此处入口拒绝chapter-insert计划，旧40.8秒草稿不代表新42.6秒插入版交接完成。

0.7另有独立分轨入口，已将42.6秒插入版登记剪映首页，字幕和章节标题/编号为原生文字、章节为图片及关键帧，见 [editable-chapter-delivery.md](editable-chapter-delivery.md)。旧cover入口仍保留原边界，不混用两种时钟。

0.5新增独立入口 `plugins/jed-video-system/scripts/chapter_delivery.py`，复用已有40.8秒连续单源试验，把已确认的章节卡接到完整预览和未发布剪映草稿。没有复制或修改ChatCut、Remotion官方插件，使用项目原有Remotion 4.0.530本地CLI和既有Jianying Bridge。

## 运行边界

从项目根运行：

```powershell
python plugins/jed-video-system/scripts/chapter_delivery.py --props work/chapters/preview-props-r1.json --review-state work/chapters/review-state-r1.json --candidate-id chapter-demo-sample-r1 --job-id 20261001-r2
```

默认只检查并规划；加 `--execute` 才调用本机工具。这些素材、计划、审片状态和本机配置不进入GitHub，克隆后需自行准备；该例只对应本次已确认真实小样，不能通过复制状态或把字段改为approved给其他视频放行。

入口核验明确的章节visual_sample批准、真实视频及递归依赖摘要、输入props路径和内容、styleId/revision。完整预览使用原props；只新增一个独立Asset composition，复用同一ChapterTransitionPreview，清空底片、字幕和口播叠层，再把章节事件移到素材自身第0帧。没有重写已确认组件，原小样批准仍对应相同像素配方。

执行顺序：完整H.264预览 → 原声校时与三窗检查 → 每个章节ProRes4444透明素材 → 既有worker隔离组装与Bridge回读。job目录位于 `work/chapter-delivery/<job-id>/`，保存输入/实现/运行时摘要、日志、音频报告、草稿结果和执行回执。成功且版本/产物不变可复用；失败或版本变化不自动重复，检查后用新job-id。执行前后核对输入，没有变化才记成功。

## 剪映中的层与时间

底片与原声、A口播透明叠层、原字幕、章节透明素材分别在四条轨道。章节放最上层，覆盖其桥段时字幕隐藏，淡出后原字幕恢复，与预览图层顺序一致；原字幕没有删除。章节视频volume=0，原声底片volume=1，字幕和转场不改变整片时长。

worker要求每个章节有唯一对应素材，绑定eventDigest与媒体SHA；拒绝缺失/孤立素材、重叠或越界、原声暂停、不匹配帧率、尺寸、时长或缺Alpha格式。该检查不替代每帧Alpha解码或剪映实际播放验收。

数字和标题在Remotion props中可编辑，导入剪映后合成在章节MOV里；剪映可以移动/替换/删除该片段，不能直接改其文字。本轮原字幕仍是剪映可编辑文字。后续若需要章节标题在剪映内直接修改，应实现独立文字/图形交接并验证排版和动画，不能将当前MOV交接描述成已有该能力。

章节配方批准与整片接受分开：receipt记录chapterRecipeApproved=true、wholeVideoApproved=false。生成独立草稿是用户已授权的准备工作，不伪造整片审片；不登记首页、不覆盖原工程、不关闭剪映。应用内播放、保存重开和原生导出继续单独验证。

## 本机实测 2026-10-01

job `20261001-r2`真实完成，重复执行返回reused=true。完整预览为 `work/chapter-delivery/20261001-r2/preview.mp4`，H.264/AAC、1920×1080、30fps、1224帧，视频与原声均40.8秒。三段原声相关性约0.995，校正后时钟偏移均0。

独立章节素材为54帧、1.8秒ProRes4444，解码yuva444p12le，首末帧Alpha为0，中间帧为近满值。Alpha检测需保留16bit灰度；直接转8bit灰度时会受颜色范围换算影响，造成假残留。该抽帧检查不宣称已逐帧或已通过剪映应用播放。

草稿 `jed-probe-chapters-20261001-r2`保存在job的隔离build目录，未登记首页。四轨、19片段、16条原字幕；章节source从0开始，target为6.8–8.6秒。结构和Bridge读回通过，未新增音效。145项行为测试、Remotion ESLint/TypeScript通过。
