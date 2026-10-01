# Jed Video System 编排插件原型 0.5

项目已有公开仓库 https://github.com/jedliuai/jed-video-system。本地插件包位于 `plugins/jed-video-system/.codex-plugin/plugin.json`；尚未安装为全局插件，也不是完全脱离工作区的通用执行包。

总插件掌握审核、用户意图、时间计划、外部后端路由与人工审片记录。ChatCut、剪映MCP/CLI、Remotion、Video Use、声音skill与agy独立存在，按需发现和调用；不将所有外部引擎内置，不再实现一套同样的认证或MCP服务。

## 已实现与仍待接入

| 模块 | 当前状态 |
| --- | --- |
| Intake | 条件问询与偏好优先级；仍为完整制作问询协议，窄任务由总skill按范围绕开无关问题 |
| Routing | 按目的编辑器与能力快照规划后端；禁止静默更换交付对象；无外部执行 |
| Human review | 候选、真实本地样片摘要、pending/approved/revise/rejected、范围与版本、依赖失效、有限批量复用 |
| Video Use | 本地缓存转录已实现；保留来源版本与逐词质量 |
| Plan compiler | 单源、单倍速、顺序裁切与共同帧时间已实现 |
| Remotion | 固定A视觉、真实原声预览与透明素材已通过本机试验 |
| Jianying draft / Bridge | 隔离组装、内联、字幕与首页事务通过；应用播放、保存重开和原生导出待验证 |
| ChatCut | Codex界面确认已安装启用；当前旧会话工具未加载，编辑和时间读回尚未实测 |
| Local dispatcher | 已接样图与未发布草稿；版本、意图、相关审片及回执；其他入口未全接，非通用执行器 |
| Chapters | host分析主要章节，校验摘要/边界依据及源版本；已确认配方接入完整预览、独立Alpha与四轨草稿，剪映UI待验收 |

机器可读状态见 `adapters/registry.json`。单次路线的`route_ready`不是生产就绪；`executionAuthorized`固定false。intake的`productionAdaptersReady=false`保持原义，避免把一个规划返回码冒充完整生产能力。

## 本轮可运行的核心

`scripts/route.py`读取请求和实际能力快照，决定各环节后端，并可输出待准备的小样要求。公开capabilities示例全部未连接。固定动效走Remotion；ChatCut可编辑图形须有对应能力；跨编辑器还需要验证媒体/透明层交接。结构检查不能替代剪映UI检查。

`scripts/review.py`提供init/register/request/decide/evaluate/suggest。记录决定只能由host根据人的明确回复填写；不自动产生approval、不认证操作者身份、不宣称已观看像素。CLI会核验实际本地文件及递归依赖摘要，不存在、改过或未经host验证的URL不会放行。

口播接受需要可听样片，动效需要真实图片/视频，声音需要可听样片；动画节奏仍需host展示完整运动。JSON计划不能批准口播的人味。批量仅可复用同范围、同范式、同修订和操作版本的视觉/声音小样。修改使受影响及下游批准失效；旧批次不会因新样片获批而自动复活。

范围授权与效果接受分别判断。已授权机械准备及隔离小样不必等审美批准；正式应用与批量扩展才检查对应接受记录。已选A和录屏不加B-roll直接复用，新的配方、语义或情绪则用具体片段判断。窄任务不用填完整问卷。

## 试验结果与下一步

本轮145项行为测试通过。章节8秒原声样片获得用户明确回复“这版可以，保留画风和节奏”，绑定此版文件及依赖；已复用同一组件接入40.8秒完整预览和未发布四轨草稿，时间、原声、Alpha抽帧及结构检查通过。章节配方批准不等于整片接受，剪映应用验收仍待完成；见 [chapter-delivery.md](chapter-delivery.md)。

下一步做剪映应用播放、保存重开与原生导出验收；章节标题在剪映内直接编辑尚未实现。在加载ChatCut工具的会话里做隔离短样，验证一处停顿、字幕同步及源/输出片段读回。可靠时间交接之前不跨编辑器双写；按实际需求扩展动作目录与旧入口审片检查，官方插件保持原样。

详细判断见 [editor-routing-and-human-review.md](editor-routing-and-human-review.md)，技能入口见插件 `skills/jed-video-system/SKILL.md`。
