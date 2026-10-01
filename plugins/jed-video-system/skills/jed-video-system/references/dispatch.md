# 本机受控执行

0.4在本项目内提供 `scripts/dispatch.py`，把路线、明确操作意图、输入版本、审片和执行回执串起来。它只接下面两项实际验证的动作，尚非通用外部工具执行器。

| action | 范围 | phase |
| --- | --- | --- |
| remotion-still | 现有ProductionPreview的一帧图片 | prepare |
| create-isolated-draft | 现有40.8秒试验计划的未发布剪映副本 | prepare或reviewed-apply |

从项目根运行 `python plugins/jed-video-system/scripts/dispatch.py --request <request.json> --capabilities <actual-capabilities.json>` 默认只检查并返回planned；加 `--execute` 才实际执行。请求结构见 `schemas/dispatch-request.schema.json`，插件示例是 `examples/dispatch-still.json`。公开能力示例全部未连接，不能改成true来冒充工具发现。调用前读取真实本机配置、运行时和后端能力。

`intent.authorizedActions`由host依据会话授权填写；JSON字段不是认证，也不能自己扩展客户授权。prepare允许获授权的隔离小样准备，无需让客户先批准还不存在的效果。reviewed-apply在本轮仅对具体rough_cut组装试验开放，检查实际批准及递归依赖，覆盖当前props、源视频、字体和透明层；一个风格样图不能代替整段版本。该模式仍只写未发布副本。

每个jobId只对应一个输入/实现/运行时/路线版本。结果位于 `work/dispatch/<jobId>/`，包括receipt.json、产物摘要及stdout/stderr。成功且文件不变时可复用结果；版本或产物变了不能复用原jobId；失败或中断保留记录，不自动重跑副作用。先检查原因，再用明确的新任务重试。

当前执行器不发布首页、不导出剪映、不通过任意shell执行用户字符串，也不伪装ChatCut或Remotion官方插件的API。Remotion的本地CLI是已有motion-lab依赖，官方插件仍按其可用工具单独调用。0.5另有 `scripts/chapter_delivery.py`连接已确认章节配方到完整预览和未发布草稿，见 [chapters.md](chapters.md)；它是独立的受控试验入口，尚未纳入此动作目录。

主skill仍负责本次相关intake约束、语义与审美判断；此入口不替代人的回复、工具身份或应用内验收。原有转录、完整渲染、章节render与Publish入口没有全部自动消费审片状态。不能绕开host检查后声称整个系统受gate保护。

需要上游项目协作时读取项目根 `docs/upstream-handoff-prompts.md`：给用户可复制提示词，由用户转交；ChatCut和Remotion为固定官方依赖，不修改其源码、skill或服务。
