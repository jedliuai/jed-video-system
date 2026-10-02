# Draft adapter（兼容探针阶段）

透明文字的编辑器兼容修复见 [透明合成记录](../../docs/alpha-compositing-compatibility.md)。`replace_overlay_media.py` 默认逐字节匹配获准样片；可选 `alphaTransport=premultiplied-rgb` 仅支持获准无边样式，并验证 Alpha 不变及固定上限的预乘颜色误差。该检查不代表剪映实播通过，不自动授权覆盖原工程。

Python worker 用既有固定 pyJianYingDraft fork 创建新工程。带测试音效的 `build` 用既有 Bridge 的 `prepare → build → verify → publish` 流程；无新音效的 `preview` 生成中性转运 manifest，用同一个 Bridge verifier/publisher 验证与登记。它不能继续编辑用户已微调的工程，不是任意 edit-plan 的完整编译器。

运行时使用本机 Bridge 的 `.venv/Scripts/python.exe`。输入为 UTF-8 JSON 文件（`--input`）或 stdin；stdout 为一行 JSON；第三方进度和错误写 stderr。命令为 `probe`、`inspect-source`、`build`、`preview`，后两者的 `--publish` 调用现有 Bridge 的首页事务。没有 `--publish` 时，仅操作项目工作目录中的隔离草稿与隔离 User Data。

输入 `build` 必需字段：

- `schemaVersion`: `jed-draft-probe/1`
- `name`: 唯一 `jed-probe-*` 名称，不能含路径符号
- `bridgeProject`、`bridgeConfig`: 本机已有桥接项目和本机配置路径
- `outputRoot`: 项目工作目录
- `source`、`overlay`、`sound`: 已存在的本机素材绝对路径
- `durationFrames`: 正整数；`fps`: 30 或 60（默认 30）
- 可选 `sourceStartUs`（默认 0）、`font`、`testText`、`soundStartFrame`（默认 15）、`soundVolume`（默认 0.08）

画布暂固定 1920×1080。视频覆层从自身 0 秒开始，持续整个探针；不允许超出已渲染时长，PNG 可作为静态覆层。底片原声保留，覆层音量为 0；测试文字单独文字轨，音效通过 Bridge 加入音效轨。

结果 `jed-draft-result/1` 包含实际轨道/片段/素材 ID、source/target 微秒范围、render_index、源文件元数据与 SHA256、Bridge manifest 路径以及分项验收状态。用户素材、字体均内联到隔离草稿；不是指向其他工程的脆弱软链接。每次 invocation UUID 独立；失败保留 `failure-report.json`，不删除或覆盖已有草稿。相同名字首页登记会被 Bridge 拒绝。

本轮 Windows Computer Use runtime 实际返回不可用。因此结构校验、MediaInfo 解析和 FFmpeg Alpha 解码结果不代表剪映播放、保存重开或导出通过。`visualLayerPlayback` 必须保持 `pending_ui_verification`，直到实际应用验收补齐。

## 无新增音效的真实预览

`preview --input <json> --publish` 接受 `schemaVersion=jed-draft-preview/1`，以及 `bridgeProject`、`bridgeConfig`、`outputRoot`、唯一 `name`、`source`、`overlay`、`font`、`renderProps`（文件路径）、`overlayDurationFrames`（本例 348）。不接受 `sound` 字段。

`renderProps` 的 `fps`、`durationInFrames`、唯一零起点 `clips`、已排序且不重叠的 `captions[{startFrame,endFrame,text}]` 为权威输入。当前只支持不中断的单个底片；多段剪切要由后续 adapter 扩展，不能默默忽略。三个轨道分别是底片及其原声、独立透明图形、可编辑字幕。16 条真实字幕保留人工修正原文，使用源计划给定的整数帧边界。

中文字用本机字体、白色、黑描边，剪映字号单位 5、文字中心 transform_y=-0.8，参考已有正式草稿的实际字号/位置。目标是 40px 字幕与底部 88px 留距，但在缺少 UI 渲染验收时不声称像素尺寸已测准。

薄层生成中性 Bridge manifest 的原因：原有 `prepare` 必须新增音效或明确合并音轨，不能通过它执行“不要加音效”的任务。初稿已完成所有画面后，转运 manifest 把它视为原始基线、记录新增音轨和音效数量均为 0，仍通过既有 `Bridge.verify` 的字段保持、素材存在、快照与哈希检查，再调用同一 `publish` 事务。没有构造虚假音效，也没有实现第二套首页更新逻辑。
