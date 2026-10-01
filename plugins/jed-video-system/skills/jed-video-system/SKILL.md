---
name: jed-video-system
description: Organize a Jed video project with conditional client preferences, content-addressed local transcription, shared frame timing, reusable motion scenes, and isolated Jianying draft creation. Use this workspace workflow while keeping editor playback verification separate from structural checks.
---

# Jed Video System

先审核素材与转录，不要把输入文件名当作内容分类。区分口播、教程录屏、混合段与分类不确定的段。时间与置信度写进 audit，不猜测已确认的客户意见。

运行 `scripts/intake.py`，使用 `examples/audit-mixed.json` 了解输入结构。项目答案高于用户明确偏好；界面里的推荐值不等于回答。`status` 不是 `ready_for_planning` 时，只处理输出的 `questions` 与 `blockers`，不能发出生产任务。

口播与录屏共存时，根据实际审核结果判断是否需要询问录屏 B-roll。已明确的 `broll.screen_recording=false` 可以复用，不重复问。禁用 B-roll 时不搜索或下载 B-roll；重点圈画、缩放、步骤标注仍属于独立的 Motion 选择。口播的 B-roll 也要经过选择，不能自动强制添加。

使用固定的组件与场景，内容通过 props 输入；画面样式目前在项目 `motion-lab` 中试验。图表例子若是合成数据必须标明，正式任务不得把它当作客户真实数据。

能力边界、问询键名和路径配置见 [workflow.md](references/workflow.md) 与插件 `adapters/registry.json`。0.2 本机阶段已可执行转录、人工计划的帧时间编译、真实原声预览、独立透明动效与隔离剪映草稿；只在原声明范围内操作。入口依赖绑定的项目根 `scripts/`、`motion-lab/` 与 `workers/`，尚未打包成脱离工作区的通用安装包。

`compile_plan.py --plan --transcript --output` 只接受来源SHA匹配的逐词转录。预览与独立动效共用输出props，不各写一套cue。沿用已选A的原画面叠层；录屏B-roll为false时不搜索下载。人工计划需要已有会话授权；它不能把尚未回答的客户偏好自动升级为生产计划。

本机完整试验入口是项目根 `scripts/prepare-live-source.ps1`、`scripts/render-live-preview.ps1`、`scripts/create-live-draft.ps1`。最后一个默认只生成独立草稿，`-Publish` 通过现有Bridge事务登记首页；剪映运行时不得强制关闭或绕过检查。生产精修尚未接入，不得擅自删除口头语或停顿，不叠加未确认的新音效。

素材Alpha解码、MediaInfo解析、草稿回读、首页登记、应用内播放、保存重开和原生导出分别记录。本轮Windows UI runtime不可用，不能把结构通过说成应用播放通过。当前安装的MCP入口缺安装目录环境，显式Bridge配置可用；不要为此重写codec或启动重复MCP。现有工具通过本地路径调用，禁止为了包装插件再开发同一底层能力。
