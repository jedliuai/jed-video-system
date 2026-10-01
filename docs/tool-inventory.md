# 现有工具调查：Jed Video System

调查日期：2026-10-01。这里把“本轮实际运行成功”“本地代码具备”“文档声明”和“仍待测试”分开写，避免把工具名字当成已经打通的能力。

## 1. 最重要的发现

本机可用的剪映 CLI、Jianying MCP 和「剪映音效助手」是同一个项目的不同入口，底层都是 `jianying_bridge.core.Bridge`。它们并不是三套互相补齐的视频剪辑引擎。

现有桥接层已经解决了很有价值的问题：读取新版加密草稿、识别多时间线、保留原工程字段、生成音效副本、校验、登记到剪映首页。但它目前暴露的编辑操作集中在音效，没有完整的视频、图片、字幕组装入口。

这意味着：只在总控里串联现有 CLI 命令，还不能实现文档描述的完整流水线。需要在新项目中增加一个薄的草稿组装适配层，调用本机已经安装的 pyJianYingDraft；保留现有桥接项目，避免重新实现加解密和音效流程。

## 2. 调查位置与版本

| 对象 | 本机位置 / 版本 | 本轮确认 |
| --- | --- | --- |
| Video Use | `C:/Users/lyjch/.codex/skills/video-use/` | Skill、README、转录与渲染 helper 已阅读；这是有本地修改的工作副本 |
| WhisperX | `D:/AI-Runtimes/video-use-whisperx/.venv/`；3.8.6 | 实际导入环境成功；Torch 2.8.0+cu128，CUDA 可用，RTX 4060 |
| WhisperX 模型 | `D:/AI-Models/whisperx/` | 已有 turbo 转录模型和中文 wav2vec2 对齐模型目录；本轮未执行新转录 |
| Remotion 插件 | 缓存版本 1.0.7；Skill 元数据 4.0.506 | 技能与透明渲染说明已阅读；插件版本不是项目 npm 依赖版本 |
| 已有 Remotion 工程 | `D:/Desktop/Jed IP/Codex专用/OBS-talk-demo-studio/motion-background/` | 实际 package 与 node_modules 为 Remotion 4.0.530；已有背景 Composition |
| 剪映接入项目 | `D:/Documents/GitHub/剪映 自动化接入/` | CLI、MCP server、Bridge、README、依赖锁定与插件配置已核对 |
| 剪映 | `D:/Program Files/JianyingPro/11.5.0.14471/` | MCP doctor 实际运行成功；本机 DLL 与草稿根目录存在；检查时剪映未运行 |
| 草稿目录 | `D:/Program Files/JianyingPro Drafts/` | CLI 列表成功，返回 108 个草稿；未批量读取这些工程 |
| pyJianYingDraft | 剪映桥接项目的 `.venv/Lib/site-packages/`；0.3.0 | 安装来源为 aoguai fork 的固定 Git 提交，不是随意安装的同名包 |
| agy | `C:/Users/lyjch/AppData/Local/agy/bin/agy.exe` | `--help` 成功，具备非交互 prompt、plan 模式和 JSON 输出选项；未调用模型设计 |
| 基础工具 | Node 24.11.0；FFmpeg/ffprobe 8.1；Python、uv、gh | 命令存在；已用 ffprobe 与 FFmpeg 检查资源 |

pyJianYingDraft 固定提交：`2b6ed48b0f096e5a76a5b8a68a6d7d233defb463`。

桥接项目当前 Git HEAD：`674ff3006943810f1cb6485874e197cb26cc62ea`。Video Use HEAD：`92c2b34e44c205cbc2acae7f6ca7c1c219d5dd66`，但 helper 和 Skill 有未提交的本地改动；仅锁 Git HEAD 不足以复现。关键文件哈希已保存到 [local-tool-audit.json](research-media/local-tool-audit.json)。

在检查过的 PATH、Codex/Agents/Claude Skill 目录及相关项目中，没有找到另一套已经可调用的通用 Windows Jianying Headless CLI。这不等于对整块硬盘做了穷举扫描。

## 3. Video Use：保留 helper，降低自由导演流程的优先级

### 可以复用

- 本地 WhisperX 转录、中文强制对齐、逐词时间戳，以及单人视频不做说话人分离的设置。
- `pack_transcripts.py`：把逐词结果压缩为便于 AI 阅读的短语文本。
- `timeline_view.py`：在剪辑决策点看胶片条与波形。
- `render.py`：FFmpeg 分段、拼接、叠加动效、最后添加字幕，作为预览和恢复路径。
- 词边界剪辑、剪辑点留余量、音频短淡入淡出、叠加素材时间归零、源时间到输出时间映射等已有经验。

### 不适合作为正常生产的总控

Skill 的默认流程强调临时设计、自由选择 PIL / Remotion / HyperFrames / Manim，并为每个动画 slot 建工程。这与固定品牌组件库直接冲突。不要修改它的 Skill；让 Jed 总控只调用需要的 helper，不启动它的完整自由创作流程。

本地已有视频项目主要包含 PIL/FFmpeg 场景脚本与历史成片，它们是可借鉴的设计与经验，不等于现成的可复用 Remotion 组件库。值得保留的已认可经验是：同一个信息模块逐层增加元素，旧元素保留到模块结束，不能把逐句同步做成每句话替换一张关键词卡。

### 代码中发现的两个限制

1. `transcribe_one()` 以 `video.stem` 命名缓存，只要同名 JSON 存在就直接返回，没有核对源文件是否变化。新 wrapper 应按源文件哈希和转录配置分配独立缓存目录，避免同名视频或替换源片后复用旧结果。
2. `whisperx_runner.py` 会对未对齐词插值补时间。格式上有时间戳不代表全部逐词边界都经过可靠对齐。新数据层应记录对齐质量和近似时间，重要落点抽查，不将 ASR 当成逐帧真值。

本轮只验证了转录环境导入、GPU 和模型目录，没有实际重跑 ASR，没有调用 ElevenLabs。

## 4. Remotion：固定视觉系统的主引擎

已经存在 npm 工程和背景 Composition `JedMidnightLoop`：2560×1440、30fps、360 帧，深蓝底、斜线、柔光独立层。可沿用它的视觉方向和工程经验；它还不包含文档要求的 SectionTitle、ComparisonBars 等品牌组件。

Remotion 适合做固定布局的标题、数字、条形图、折线图、来源卡和截图窗口；内容通过 JSON props 输入，逐帧确定动画。同一个组件供 Gallery 和正式渲染共用，避免“预览好看、正式导出另一套代码”。参数化能力与 Player 可分别参见 [参数化视频](https://www.remotion.dev/docs/parameterized-rendering) 和 [Player 文档](https://www.remotion.dev/docs/player)。

不把它当成音频转录器、剪映工程编辑器，也不让它接管每段真人素材与 B-roll。复杂实拍剪辑留在剪映，Remotion 主要产出独立的信息图素材。

透明 MOV / WebM 的渲染配置已核对官方资料，但本轮没有渲染测试片，也没有在剪映中测试 Alpha 导入。不能据此说透明链路已经通了。

旧 OBS 工程 `package.json` 标有 `GPL-2.0-only`。新公开仓库若要复制其源代码，应先核对实际项目许可；本方案先建议复用视觉方向，不直接复制整套工程。

## 5. Jianying CLI、MCP、音效插件：同一个底层

### CLI 已有命令

`doctor`、`guide`、`list`、`inspect`、`audio`、`cached-audio`、`prepare`、`build`、`verify`、`publish`、`mcp`。

本轮直接运行 CLI 的 `--help`、`list`、`inspect`。MCP 运行了 `jianying_doctor` 和 `get_jianying_sound_design_guide`。

### MCP 已有工具

环境检查、草稿列表、分页读取轨道和字幕、本地音效列表、缓存音效检索、准备音效计划、生成副本、校验副本、登记首页，总计 10 个工具。`server.py` 的这些工具最终调用与 CLI 相同的 Bridge 方法。

### 已有编辑能力

- 保留原工程，生成完整副本；处理加密草稿和主时间线镜像。
- 按时间加入音效，设置素材截取、时长、音量与淡入淡出。
- 默认单轨多独立片段，显式指定 ID 后合并旧音效轨道。
- 拒绝不允许的重叠、静音/锁定状态冲突、源工程变化与素材丢失。
- 音效文件复制进副本，支持剪映保存后的路径占位符和相对路径。
- 登记首页前检查剪映运行状态，保留索引备份。

### 没有暴露的能力

新建完整视频工程、插入任意视频或图片、批量创建文字字幕、全局剪辑/变速、设置视频转场和特效、透明视频控制、原生自动导出。

特别注意：`build` 中出现 `ScriptFile`，不代表 CLI 已支持任意 ScriptFile 构建。现有实现只用它生成新增音频，再合并进原工程；音效计划不能延长原工程时长。

### 当前真实草稿回读

读取与案例对应的“9月30日 个人订单驾驶舱-音效加强版”成功：新版加密、多时间线，1920×1080、60fps，时长 40.783333 秒。当前共有 22 个片段：1 个视频片段、16 个文字片段、3 个综合音效片段和另一条音频轨道上的 2 个片段。

这份结果证明本轮确实能读取当前加密草稿与字幕；不证明视频组装、写回或透明解码已经通过。历史 README 中的 337 片段 / 679 素材是此前另一版本测试记录，不能当成当前草稿的结构。

详情见 [draft-inspect.json](research-media/draft-inspect.json)。它是本地调查资料，不应直接进入公开仓库。

### 以后如何分工

- 批处理、可重复音效任务：调用现有 CLI。
- 聊天中查看工程、查询缓存、调整声音：可以调用同一能力的 MCP。
- 音效助手 Skill：保留声音选择、密度与试听经验；它是操作指南，不是另一套渲染引擎。
- 视频组装缺口：新项目 wrapper 调用现有 pyJianYingDraft，先独立验证，再接入总控。

MCP 不会自动补齐 CLI 所缺少的视频能力。两种入口也不能并行修改同一草稿；总控要串行执行并追踪最新副本。

## 6. pyJianYingDraft：已安装的能力，尚待接入

在实际安装的 Python 包中查到：`create_draft`、`append_track`、`add_segment`、`import_srt`、视频转场和色度抠图接口。视频/图片素材使用 MediaInfo 解析，因此格式测试要覆盖“Remotion 输出—素材解析—剪映显示”三个环节。

以下属于已安装 API / fork 文档声明，并非本轮在剪映 11.5 上的播放验收：

| 能力 | 接入判断 |
| --- | --- |
| 视频、图片、源片截取与目标时间 | 新 adapter 的首批功能 |
| 多轨、缩放、位置、不透明度 | 有接口；轨道叠放顺序要单独验证 |
| SRT、文字样式、本机字体 | 有接口；字体缓存和静态字体需验证 |
| 转场、关键帧、片段动画 | 有接口；只先接少量本机验证过的效果 |
| 蒙版、模板导入、复杂工程保留 | 版本差异明显，不能作为第一版必需条件 |
| 新版剪映自动导出 | 不能依赖其旧 UI 自动化导出路径 |

版本能力表与本地读取器说明见 [固定提交 README](https://github.com/aoguai/pyJianYingDraft/blob/2b6ed48b0f096e5a76a5b8a68a6d7d233defb463/README.md)。新 adapter 使用当前固定 fork；不要以安装同名 PyPI 包代替，也不要另写草稿加解密实现。

## 7. Jianying Headless 与 agy

此前桥接项目调研过 [Jianying Headless](https://github.com/mcncarl/jianying-headless)，但未作为本地 Windows 草稿依赖。本轮检查其公开说明：原生草稿/引擎链路主要面向 Apple Silicon Mac；新增 Windows FFmpeg 导出路径不生成可编辑剪映草稿。因此它不适合作为本机草稿组装的默认后端。

agy 的命令入口存在，支持 `--mode plan`、`--print`、`--output-format json` 等。这里只验证入口，不宣称模型连接或设计质量已验证。未来可把同一份品牌 brief、props 和 Gallery 样例交给 agy 出 B 版，与 Codex A 版并排比较；选定后将版本纳入组件库，正常生产不再逐视频找 agy 重设计。

## 8. 重叠与冲突处理

| 重叠 / 冲突 | 推荐处理 |
| --- | --- |
| CLI 与 MCP 对同一 Bridge 的重复入口 | CLI 管生产；MCP 管交互调查与必要恢复 |
| Video Use EDL 与 edit-plan 两份时间安排 | edit-plan 是唯一权威计划；EDL 仅由 adapter 派生 |
| Video Use 临时动画与固定 Remotion 库 | 正常生产只允许注册组件；实验动画单独管理 |
| FFmpeg 与剪映同时烧字幕 | 剪映保留可编辑字幕；FFmpeg 仅在预览 / 独立成片中最后烧字幕 |
| 总控音效规则与插件音效建议重复决策 | 总控产出一份声音计划，插件 / CLI 负责解析素材与执行 |
| 重建工程覆盖人工微调 | 初次生成与继续编辑分开；继续编辑基于最新保存副本 |
| 一个软件名称对应多个版本 | 锁 npm 版本、Python fork 提交、剪映 build 与本地 helper 哈希 |

结论：保留现有底层能力，收紧它们的职责。主要新工作是品牌组件库、计划协议、时间映射、适配层和验收流程。
