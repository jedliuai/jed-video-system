# agy 调用记录与 B 版来源

本文提及的原始 JSON、调用 brief 与 stderr 仅保留在本地，不随公开仓库分发；仓库保留可读设计规格与本说明。

日期：2026-10-01。

当前结论：后续修复终端临时代理后，AGY 已真实返回视觉评审。当前正式 B 版 `AgyTalkingHeadScene.tsx` 由 Codex 按该评审实现；旧 `CodexFallbackTalkingHeadScene.tsx` 作为自主备选保留，来源分别明确。没有对不同模型作质量评比。

## 认证恢复后的真实评审

根 agent 确认用户 CMD 认证有效，工作终端需要临时代理。仅在执行 AGY 的当前 PowerShell 进程里设定 HTTP_PROXY、HTTPS_PROXY、ALL_PROXY 指向 `http://127.0.0.1:7897`，NO_PROXY 为本机地址，没有修改持久配置或再次登录。

精确任务见 `review-brief.txt`。第一次评审采用 plan 模式、不指定 model、不跳过权限，180 秒时触发 CLI 上限。虽然 JSON 标记 SUCCESS、退出码为 0，但 response 为空，stderr 明确说明 turn in progress / returning partial output，所以该次没有被当作最终设计。

随后通过保存的 conversation_id 续同一会话，使用 `review-followup-brief.txt`，要求不再读图或调用工具、直接给出已经形成的规格，时间上限 120 秒。本次实际成功返回非空设计 response，退出码 0。原始结果为 `review-followup-response.json`，可读规格为 `review-design-spec.md`。

AGY 在返回结果中声明实际审阅了 resource-analysis、talking-head.jpg、personal-contact.jpg、A/B content、B 组件，以及 reference-contact 和连续采样图；它明确说明未逐张读取 8 张独立原始 PNG。不会把其抽样分析描述成看过全部原图。最终设计保持 A/B 相同文案。

采纳的设计：左栏 x=96、width=520；主标题 56px、第二行暖金；Eyebrow 回到顶部；右栏 x=1520、width=330；要点固定 34px、编号 24px、详情 24px；保留细分割线，移除扫入金线；统一 10px 位移缓出，按照 content.points 的 cueFrame 逐层进入。实现为独立 `AgyTalkingHeadScene`，通过结构兼容的 content props 替换内容，不依赖 A 的具体组件。

实现修正：AGY 的“单行标题”与“任意 6–10 字稳定展示”在 330px 栏宽里不能同时成立。实现保留统一 34px，以 grid 分配编号和正文，较长标题自然换行、不裁切；当前 8 字默认标题可单行显示。这是尺寸约束下的工程修正。

正式 B 组件已经格式化，visual-b ESLint 及当前项目 TypeScript 检查通过；最终渲染由总控统一进行。

## 首次失败历史

精确 brief 保存于 `brief.txt`。执行位置是项目根目录，仅申请设计规格，使用 plan 模式，没有跳过权限，没有指定未经验证的模型，没有编辑外部工程。

第一次命令参数为 `--mode plan --output-format json --print-timeout 180`，退出码 2；CLI 要求时间长度带单位，报 `time: missing unit in duration "180"`。当次输出保存为 `attempt-1-response.json`、`attempt-1-stderr.txt`、`attempt-1-exit-code.txt`。

仅重试了一次，把 timeout 改为 `180s`。CLI 提示 `Authentication required`，等待认证 60 秒后退出，退出码 1。结果为 `status: ERROR`、`authentication failed or timed out`，`num_turns: 0`，token usage 全为 0。完整原始 stdout/stderr 分别保存为 `response.json` 和 `stderr.txt`。未替用户完成登录，未改变认证状态，未启动可见登录界面。

## 自主备选的依据

Codex 读取了 `docs/resource-analysis.md`，实际查看了 `docs/research-media/personal-contact.jpg` 与 `motion-lab/public/talking-head.jpg`。人物实际位于偏右中央，原始底片有烧录字幕与左侧旧包装。因此左侧采用深蓝渐变覆盖旧包装，主观点直接排字；右侧采用细线、编号和三个短步骤；人物面部保持无遮挡，底部原字幕保持可见。该布局只做画面样式预览，不宣称已经匹配口播语义。

B 版采用 1920×1080、30fps、180 帧。左侧 x=84..624，右侧 x=1518..1830；中间保留人物。主观点 60px、步骤 42px、辅助说明 24..27px；顶部和角落小标签 19..24px。颜色沿用文档中的 Jed 深蓝、亮蓝、暖金。

入场为 12 帧缓出、14px 位移；主观点逐行在第 5、12、19 帧建立；三步骤在 30、56、82 帧开始建立并持续保留，最后一步完成后仍有近 3 秒阅读时间。所有状态由 useCurrentFrame 决定，没有随机、时钟或弹跳动画。

组件文件是 `motion-lab/src/visual-b/CodexFallbackTalkingHeadScene.tsx`。今后 agy 登录可用后，可复用同一个 brief 真正生成视觉对照，并保留这份失败记录。

组件已用项目内 Prettier 格式化，针对该组件的 ESLint 检查通过，当前项目 TypeScript 检查通过。渲染与最终画面验证由总控统一进行；本 agent 未自行渲染整个项目。

后续调整：B 版已拆出 `content.ts`，其内容结构与 A 版 TalkingHeadContent 兼容，但没有引用 A 版实现。为便于真实 A/B 比较，当前默认内容同步实际 A 版：两行标题“把复杂的事，讲得更清楚。”、两条要点“先保留人物的表达”“再建立信息的层次”。可由总控给两个 Scene 传入同一个 content 对象。长要点采用 32px 并换行，短要点为 42px。组件已重新通过 ESLint 与 TypeScript 检查。前面的三步 brief 与首次设计记录保留，避免改写历史。
