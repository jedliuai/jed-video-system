# 本机兼容矩阵

日期：2026-10-01。剪映 build：11.5.0.14471；pyJianYingDraft：本机已固定的 0.3.0 fork，提交 `2b6ed48b0f096e5a76a5b8a68a6d7d233defb463`；目标画布 1920×1080。探针为 3 秒、30fps，比较同一份透明图形。

“通过”只在对应列成立。FFprobe 发现 alpha 字段和 FFmpeg 解出透明像素，不能替代剪映播放 / 保存 / 导出结果。

| 格式 / 能力 | 文件与解码 | 固定 fork MediaInfo | 新草稿结构 | 剪映打开 / 层级 / 透明播放 | 保存重开 | 剪映导出 |
| --- | --- | --- | --- | --- | --- | --- |
| ProRes 4444 MOV | 通过：4444 / yuva444p12le，90 帧 / 3s；RGBA 角落 alpha=0、半透明块=129、金色圆=255 | 通过：1920×1080 / 3s | 通过：四轨四片段，已首页登记独立副本 | 待 UI 验证 | 待 UI 验证 | 待 UI 验证 |
| VP9 Alpha WebM | 通过：显式 libvpx-vp9 解出 RGBA，角落 alpha=0、半透明块=129、金色圆=255 | 通过：1920×1080 / 3s | 通过：四轨四片段，已首页登记独立副本 | 待 UI 验证 | 待 UI 验证 | 待 UI 验证 |
| 单张透明 PNG | 通过：RGBA 角落 alpha=0、半透明块=128、金色圆=255 | 通过：1920×1080；库静态素材默认时长 3h | 通过：实际片段限定 3s，四轨四片段，已首页登记独立副本 | 待 UI 验证 | 待 UI 验证 | 待 UI 验证 |
| 原视频截取 + 可编辑测试文字 + 独立音效 | H.264 原底片 / AAC 原声；0.18s WAV 提示音已生成 | 通过 | 通过：0–3s 底片、覆层、文字，0.5–0.68s 音效；Bridge 保留 3 个初稿片段 | 待 UI 验证 | 待 UI 验证 | 待 UI 验证 |
| 真实 40.8s 工程 / 11.6s 透明动效 / 16 条可编辑字幕 | 原底片含原声；没有新增音效 | 通过：底片与实际动效素材可读 | 通过：3 轨 / 18 段，全部字幕匹配统一 props，媒体和字体均内联且存在，首页登记与回读成功 | 待 UI 验证 | 待 UI 验证 | 待 UI 验证 |
| 0.6独立章节停顿 / 42.6s完整候选 | H.264/AAC、1278帧；原口播映射与音效专属区间校时通过，小样衔接获用户确认 | 未交接 | 尚未实现插入版草稿，旧cover工程不等同 | 待接入 | 待接入 | 待接入 |

## 工具入口

| 入口 | 结果 | 实际含义 |
| --- | --- | --- |
| Bridge 显式本机配置读取当前正式草稿 | 通过 | 新版加密、多时间线和全部 16 条文字可读；未修改原工程 |
| 早期 Jianying MCP inspect | 当时失败：缺 `JY_INSTALL_DIR` | 历史入口环境问题；显式 Bridge 可用，不另写 codec |
| 0.6本轮 Jianying MCP doctor / 声音指南 / 缓存查询 | 通过 | 安装/草稿目录与codec可用，取得本机转场声音；未认证重登、未重复启动服务，不等于写入或UI验收 |
| Windows Computer Use 官方 runtime 初始化 | 不可用 | 返回 `Windows Computer Use Sky runtime is unavailable`；不能执行 UI 验收 |
| Worker 非整数 fps、未知版本、路径型名字、越界 cue | 已拒绝 | 只宣告本阶段已实际实现范围 |

## 待补的应用验收

在独立 `jed-probe-*` 草稿里，底片应正常播放，透明角落露出底片，半透明蓝色块与底片混合，蓝色文字和金色圆形位于底片上方。文字轨的中文可选中修改，音效位于 0.5 秒处，原声保留。保存后回首页，再次打开，确认四轨、素材定位、时长和透明显示；导出 3 秒 MP4，检查透明处没有变成黑底、中文字边缘正常，提示音没有错位。

该步骤目前是待验收说明，不是已完成的测试记录。原正式工程不参与这轮探针。

## 本轮生成的独立工程和证据

首页登记成功且三个工程名称各不相同：

- `jed-probe-mov-20261001-9a732e9e`
- `jed-probe-webm-20261001-f752b654`
- `jed-probe-png-20261001-f39c7c1e`

位置均在本机草稿根 `D:/Program Files/JianyingPro Drafts/`。每次 `Bridge.publish` 的实际结果、索引备份路径和 invocation manifest 路径保存在项目本地 `work/compatibility/draft-build-{mov,webm,png}-result.json`。首页登记检查时剪映未运行；本轮没有通过自动关闭软件来满足要求。

`work/compatibility/draft-media-report.json` 包含固定 fork 实际解析结果与安装来源，`draft-alpha-report.json` 保存真实 RGBA 像素抽样。三份 manifest 的实际视觉轨道 render_index 为 0（底片）、1（透明素材）、2（可编辑文字），音效为 3；这只是生成结构的证据，应用实际叠放仍待验证。

WebM 的 FFmpeg 默认 VP9 解码器可能不提供 Alpha；本轮明确用 `libvpx-vp9` 解码并检查像素。这个解码选择不能推断剪映内置解码器的表现。

首批三格式探针的 meta `draft_root_path` 仍是 staging 根，但首页 entry、草稿路径和素材路径正确。worker 在发现后已为后续构建修正该父目录字段；未追改已经登记的探针。真实 `jed-probe-live-20261001-a726bdf2` 采用修正版，实际回读确认 sidecar 根、草稿路径和名称全部正确；证据为 `work/compatibility/draft-live-readback.json`。
