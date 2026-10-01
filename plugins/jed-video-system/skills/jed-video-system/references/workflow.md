# Workflow boundaries

`audit -> pending questions / blockers -> intake intent -> explicitly authored edit-plan -> frame compiler -> validated adapters`

0.5包含外部路由与人工小样审核，见 [orchestration.md](orchestration.md)，本机两项受控动作见 [dispatch.md](dispatch.md)，结构、章节转场与已确认配方的独立交接见 [chapters.md](chapters.md)。总控流程为audit → 相关范围授权 → 只读route → 候选/小样自检 → 人工接受适用范围 → 实际调度 → 验证。原0.2其他入口仍可按已有人工计划授权使用，尚未全部自动消费review记录；intake的productionAdaptersReady=false保持不变。

从插件根目录运行：

```powershell
python scripts/intake.py --audit examples/audit-mixed.json --profile ../../config/user-preferences.example.json --answers examples/project-answers.json
```

命令只读输入，向标准输出发出 JSON；使用 `--output` 可保存结果。问询缺失或转录未准备好时退出码为 2；输入格式或答案值无效时为 1；偏好可用于下一步规划时为 0。即使退出码 0，也不意味着生产 adapter 可执行。

键名：`broll.talking_head`、`broll.screen_recording`、`motion.screen_recording`、`speech.edit_mode`、`sound.mode`。偏好使用相同键。分类覆盖放在项目答案 `classifications` 映射中；视频分类与具体段关联，不能保存成通用用户偏好。

只在可达的条件分支问问题：低置信或 unknown 的段先分类；分类确认后才问相关视觉偏好。有语音才问语音编辑；选择 `review_trim` 需要已对齐转录。纯录屏原型保留原操作画面，不提供 B-roll 规划；混合素材才询问录屏 B-roll。纯录屏需要 B-roll 时属于下一阶段扩展，不能悄悄安排素材。

插件根目录 `adapters/registry.json` 是能力登记，不是可执行器。外部路径由项目根目录 `config/local.json` 提供（从 example 复制，保持本地），不写入插件公共 manifest。MCP 继续复用已安装服务，本轮入口缺安装目录，显式Bridge配置读取可用。0.2 已验证转录、手写计划编译、真实预览与隔离草稿；不复制服务。

工作区入口顺序是 `scripts/prepare-live-source.ps1 → scripts/render-live-preview.ps1 → scripts/create-live-draft.ps1`。最后一个默认隔离保存，显式 `-Publish` 才用原Bridge登记首页。新底片与ASR输入不同，需要独立音频时间绑定；预览与透明层共用同一帧props。剪映应用中的透明播放/保存重开/导出仍待验证，不扩展为任意旧工程编辑或原生全自动导出。
