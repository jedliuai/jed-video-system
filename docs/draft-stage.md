# 新草稿适配层：第二轮实现

日期：2026-10-01。状态：薄 worker、边界校验、三格式探针及真实 40.8 秒可编辑草稿构建、首页登记和结构回读已完成；应用播放、保存重开和导出待验证。格式探针结果见 [兼容矩阵](compatibility-matrix.md)。

入口为 `workers/draft-adapter/worker.py`，在现有剪映 Bridge 的虚拟环境运行，不额外安装同名 PyPI 包。当前支持新建 1920×1080、整数 30/60fps、一个底片截取、一个独立覆层；兼容探针 `build` 加一条测试文字和一条音效，真实 `preview` 从统一 render props 创建逐条可编辑字幕并严格不新增音效。尚不承担任意 edit-plan 编译、复杂变速、旧工程继续编辑或原生自动导出。

## 实际调用链

1. FFprobe 检查素材存在、源范围、覆层渲染时长；整数帧起止各自转微秒。
2. 已安装固定 fork 的 `DraftFolder.create_draft`、`append_track`、`insert_track(over_track=...)`、`VideoSegment`、`TextSegment` 创建本地初稿。
3. `DraftFolder` 指向项目里的隔离 User Data。这个细节很关键：fork 的 `save` 会执行注册 hooks，不能让临时初稿隐式落到用户实际首页索引。
4. 调用现有 `Bridge.prepare → build → verify`，在新副本中加入测试音效，沿用其路径重映射、字段保持和素材校验。
5. 仅 `--publish` 才调用现有 `Bridge.publish`，用实际本机配置登记唯一的 `jed-probe-*` 副本。首页事务仍由 Bridge 负责检查剪映运行状态、索引是否变化、备份以及禁止覆盖；worker 不另写加解密或首页逻辑。

每次调用产生新 invocation UUID；失败保留报告。root 插件应读取 worker 返回的 `manifest`，追踪副本而非猜草稿路径。后续音效不能回头继续修改 baseline。

## 数据边界

输入协议 `jed-draft-probe/1` 是此阶段的探针请求，不是正式 edit-plan 协议。具体字段见 worker README 和 `probe-input.example.json`。输出协议 `jed-draft-result/1` 记录源文件 SHA256、媒体元数据、实际项目 ID、轨道 ID、片段 ID、material ID、render_index、源与目标微秒区间以及逐项验收结果。

新原声由底片视频保留；动效覆层音量为 0；测试提示音为本机 FFmpeg 合成的 0.18 秒 880Hz 短音，不使用来源不明的音乐。测试文字单独文字轨；已有字幕不是测试文字，后续需由真实字幕计划按时间创建。

结构层可以确认 API 输出的轨道顺序和 render_index。它不能证明剪映渲染层级。视觉层级、透明边缘、中文字体实际显示、播放、保存重开和剪映导出都必须由应用中的结果补齐。

## 真实案例的只读回读

当前正式“9月30日 个人订单驾驶舱-音效加强版”有 1 个视频段、16 个独立文字段和 5 个音频段；已用配置明确的 Bridge 解码读取全部文字，写入本地 `work/compatibility/draft-source-captions.json`。源视频截取区间是 98.45 秒起、40.783333 秒长。该正式草稿本轮没有写入。

正式草稿引用的“视觉精修”视频抽帧确认仍已烘左侧提示和右下署名，尽管没有烘底部字幕。后续真实预览改从原始“手动粗剪1.mp4”提取，避免重复侧栏；不能将包装片误称裸原片。

## 目前的验收限制

本轮完整读取 Windows Computer Use skill 后，按其唯一初始化入口调用 runtime，实际返回 `Windows Computer Use Sky runtime is unavailable`。因此未改用历史自动点击脚本伪装 UI 验收，也没有关闭用户工程。文档和 manifest 必须保留 UI 待验证状态。

另一个发现：本轮 MCP inspect 入口缺少 `JY_INSTALL_DIR`，加密读取失败。相同草稿通过显式配置了安装目录的 Bridge 正常读取。这是入口环境缺项，不代表 codec 或正式工程损坏。总控应检查 runtime 配置，并使用经验证的显式 CLI/worker 配置。

10 项边界和拒绝测试覆盖 30/60fps 连续边界、长时间不累积漂移、非法时长、路径型草稿名、未知版本/fps、越界 cue、缺失素材引用、真实字幕排序/越界、尚未支持的多段截取和禁止给 preview 附带新音效。真实格式兼容由各格式探针补充；不把单元测试通过写成剪映验收完成。

新发现的路径细节：fork 新建草稿会将 `draft_meta_info.draft_root_path` 写为本地 staging 根，而现有 publisher 仅替换草稿内部路径前缀。worker 现在在初稿阶段就用现有 codec 将该 sidecar 字段设为配置中的实际发布根，再制作快照和校验。首批已登记的三个格式探针保留原状态；首页 entry 和所有素材路径正确，但 sidecar 根还是 staging，这个差异要在后续应用验收观察是否被剪映整理。真实工程采用修正后的路径。

## 真实 40.8 秒可编辑工程

本轮生成并通过现有首页事务登记的工程为 `jed-probe-live-20261001-a726bdf2`，本机路径 `D:/Program Files/JianyingPro Drafts/jed-probe-live-20261001-a726bdf2`。

源为从未包装视频提取的 `live-source.mp4`，项目 1920×1080、30fps、1224 帧，即 40.8 秒。其原声放在底片视频内，音量 1；没有另造口播音轨，没有新增提示音或 BGM。独立 ProRes 4444 透明素材在第二画面轨，仅覆盖 0–11.6 秒；之后录屏保持原画面。第三轨含 16 条可编辑文字，来自已有正式工程的人工作业版本，并由统一 render props 编译到目标帧。

实际发布文件的只读回读验证了：三轨对应 1 个底片、1 个透明层、16 个文字段；所有字幕文字和微秒范围与 render props 完全一致；所有音视频与字体文件都内联到该草稿并且存在；meta 的根路径、草稿路径和名称一致；首页索引中仅有一个对应 ID。结果为本地 `work/compatibility/draft-live-readback.json`，构建/发布结果为 `draft-build-live-result.json`。

无新音效的 preview 不通过必须添加音效的 prepare 硬塞素材。薄层只为已经组装好的初稿制作中性快照和转运 manifest，新增音效/轨道数量均为 0；字段保持、快照、素材校验与首页原子事务由既有 Bridge 完成。原有正式工程不作为可写基线。

这份结果证明真实素材已经变成独立可编辑草稿，而不是把整段 MP4 当成唯一片段。它仍不证明剪映里透明播放、字幕实际像素大小或保存重开的正确性；这些项保持 pending。
