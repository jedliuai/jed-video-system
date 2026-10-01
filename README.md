# Jed Video System

把现有剪映桥接、Remotion、Video Use 与专项 skills 组合为一个本地制作插件。已完成视觉与问询、真实转录、统一帧时间计划，以及原声预览到独立剪映草稿的本机试验闭环；完整成片流水线逐步接入。

本地0.6已实现独立章节停顿：原口播完整保留，插入1.8秒图片动画与短音效，再接下一句。用户已认可新版音效和衔接；42.6秒完整候选与9.8秒语境小样已生成，157项行为测试通过。原有受控动作、章节结构、审片及连续原声cover草稿交接保留，插入版尚未接入剪映草稿。批准绑定真实样片、范围和版本，变化只使相关批准失效。ChatCut已安装启用，当前旧会话工具尚未加载；剪映MCP本轮只读能力调用成功。分工见 [编排与人味确认](docs/editor-routing-and-human-review.md)，新版见 [章节停顿与声音](docs/chapter-insertion.md)，旧交接见 [章节交接](docs/chapter-delivery.md)。

公开仓库：[jedliuai/jed-video-system](https://github.com/jedliuai/jed-video-system)。当前是需要绑定本机环境的模块化原型，尚不是可跨机器直接安装的完整插件。

仓库包含源码、JSON Schema、配置模板、测试和阶段文档。个人素材、参考媒体、字体、渲染结果、转录缓存、实际剪辑计划和本机配置保留在本地；下文中的 `work/` 产物和剪映工程名是已完成的本机验证记录，克隆仓库不会附带这些文件。真实素材流程还需要自行准备输入计划和可用的 Video Use / Jianying Bridge 环境。

## 源码检查

在项目根运行 `python -m unittest discover -s tests -p '*_test.py'`；在 `motion-lab` 安装依赖后运行 `npm run lint`。基础行为测试不要求个人素材或剪映安装，实际转录、渲染与草稿试验另需本机依赖。

## 本轮可看的结果

- `work/chapter-insert/20261001-r2/sample.mp4`：9.8秒新版语境小样，用户已认可“口播暂停、章节动画＋短音效、接着说话”的音效和衔接。
- `work/chapter-insert/20261001-r2/preview.mp4`：42.6秒完整候选，原40.8秒口播完整保留，章节与音效占独立1.8秒。整片尚未获审片接受，未生成插入版剪映草稿。
- `work/chapter-delivery/20261001-r2/preview.mp4`：旧40.8秒连续原声cover预览，留作历史对照；配套四轨剪映副本在隔离目录，应用验收待完成。
- `work/renders/jed-chapter-transition-sample.mp4`：8秒真实原声小样，用户已确认本版画风和节奏；该记录不等于整片批准。

- `work/previews/jed-live-preview.mp4`：40.8秒真实原声样片，源码获取与演示信息跟随讲述，录屏完整保留。
- 剪映首页 `jed-probe-live-20261001-a726bdf2`：底片、11.6秒透明层和16条可编辑字幕分轨保存；应用播放和保存重开待验证。

- `work/previews/jed-style-preview.mp4`：18 秒、1920×1080、30fps，依次展示口播信息层、比较图表、教程录屏。
- `work/previews/talking-head-b.mp4`：6 秒，agy 实际评审后的另一版口播布局。
- `work/previews/index.html`：样片和静态样图预览页。
- `motion-lab/`：可复用的 React/Remotion scenes，内容、品牌 tokens 与动画实现分开。
- `plugins/jed-video-system/`：插件骨架与客户 intake 原型，具体能力见其文档。

第一轮18秒样片使用静态采样帧，图表数据为示例。第二轮40.8秒样片使用没有旧侧栏与字幕包装的原底片，保留原声与完整讲述，复用人工修正字幕；切入录屏后不加B-roll。两轮产物保留供对照。

已根据用户反馈选择 A 版口播：原画面直接承载元素，去掉深色底和渐变遮罩。选择记录在 `config/visual-preferences.json`，录屏不加 B-roll 的明确偏好记录在本地 `config/user-preferences.json`。

## 重现视觉预览

复制 `scripts/preview-local.example.json` 为 `scripts/preview-local.json`，填写素材、字体和现有 Chrome 的本机路径。这个配置不进入版本管理。

1. 在 `motion-lab` 安装锁定的依赖：`npm ci`。
2. 在项目根运行 `pwsh -File scripts/prepare-preview.ps1`。
3. 运行 `pwsh -File scripts/render-preview.ps1`。
4. 在 `motion-lab` 运行 `npx remotion studio --no-open`，逐帧预览各 composition。

复用已有 Chrome 可避免重复下载浏览器。原始个人素材、导出物和本地运行环境路径均不进入版本管理。渲染入口使用同一组件库，参数文案集中在各 `content.ts`。

## 模块边界

新增插件的接入调查见 [ChatCut 环节与分工](docs/chatcut-integration-research.md)。推荐优先验证口播脚本精修、字幕与可编辑预览；当前 ChatCut 编辑接口尚未在本轮会话可用，未将其标为已接入生产。

| 模块 | 职责 | 当前阶段 |
| --- | --- | --- |
| Intake | 审核结果 → 条件问题 → 偏好与项目答案 → 约束 | 规则原型 |
| Dispatcher | 操作意图、版本、相关审片 → 固定动作 → 回执/复用 | 已验证样图与未发布副本；非通用执行器 |
| Chapters | 主模块边界、摘要、统一参考图 → 动效与源/输出时间映射 | 插入停顿与短声音小样获认可；cover草稿保留；新版草稿待接入 |
| Motion library | 品牌、版式、动画、可参数化内容 | 三种场景与口播变体 |
| Video Use adapter | 内容键缓存转录、逐词边界质量 | 真实GPU转录已接入 |
| Plan compiler | 源秒时间、词anchor、字幕 → 共享帧props | 已实现30/60fps、仅1倍速 |
| Jianying adapter | 隔离草稿组装、内联、首页登记 | 结构通过；应用验收待验证 |
| Sound adapter | 外部声音skill与MCP缓存 → 有效截取、增益/淡变、章节区间 | 短转场真实预览获认可；通用客户生产编排待接入 |
| Plugin packaging | 统一入口、skills、环境绑定与能力检查 | 骨架，不是完整可安装生产插件 |

真实试验按顺序运行 `scripts/prepare-live-source.ps1`、`scripts/render-live-preview.ps1`、`scripts/create-live-draft.ps1`。最后一个默认隔离保存，显式加 `-Publish` 才登记新草稿首页。配置来自未提交的 `config/local.json`；人工计划位于 `work/plans/live-edit-plan.json`。先完成剪映应用验收，再连接自动规划与精修。说明见 `docs/production-pilot.md`、`docs/compatibility-matrix.md` 和 `docs/plugin-design.md`。

ChatCut和Remotion官方插件按用户要求保持原样。需要用户转交其他项目的最小调整提示词见 [上游协作提示词](docs/upstream-handoff-prompts.md)，当前无必须阻塞本机试验的上游改动。
