# 客户问询：先审核，再只问相关的问题

这版是可运行的规则原型，尚未自动识别视频。先由素材审核写 `audit`：每段类型、置信度、时间范围、有无语音，以及转录是否已对齐。示例 audit 是合成数据，不是对现有 40 秒视频的自动识别报告。

规则不要求客户填一份长问卷。比如审核发现“开头口播，后面教程录屏”，才会出现录屏 B-roll 分支；系统里已保存明确的“录屏一般不加 B-roll”时，直接复用这个选择，不重复询问。项目里明确回答要加，则只覆盖这次项目。

## 目前会问什么

| 条件 | 问询键 | 问题 / 可选值 |
| --- | --- | --- |
| unknown 或分类置信度低于 0.8 | `classify.<segmentId>` | 先确认这一段是口播 / 录屏 / 其他，暂不问后续剪辑偏好 |
| 有口播段 | `broll.talking_head` | 口播要不要 B-roll；不强制添加 |
| 口播和录屏共存 | `broll.screen_recording` | 录屏要不要 B-roll；已有明确偏好不重复问 |
| 有录屏段 | `motion.screen_recording` | 要不要圈画、局部放大或步骤标注 |
| 有语音 | `speech.edit_mode` | 保持节奏，或先生成可审核的精修候选 |
| 有视频内容 | `sound.mode` | 无音效 / 少量提示 / 明显节奏增强 |

`false` 是有效回答，不能当成缺失。推荐值只显示在 `questions.suggested`；它不进入已确认决策。录屏 B-roll 为 false，不会禁用录屏圈画与缩放，也不会允许搜索或下载 B-roll。原型的纯录屏分支保持原操作画面，不生成 B-roll 计划；需要纯录屏 B-roll 的特殊项目留给下一阶段扩展。

## 输入与输出

输入协议分别在 `schemas/intake-audit.schema.json`、`intake-answers.schema.json`、`intake-profile.schema.json`。输出在 `intake-result.schema.json`。外部 Schema validator 应把这四份本地 Schema 按 `$id` 加入 registry，profile 引用 answers 的偏好定义，不需要网络获取。运行时还校验段 ID 唯一、时间区间合法、分类覆盖引用有效与答案类型正确。

优先级是 **项目明确答案 > 用户明确偏好 > 未回答**。没有以“系统默认”冒充客户确认这一层。示例 profile 只保存用户已表达的 `broll.screen_recording=false`；其他意见要在项目问询中确认。复制成 `config/user-preferences.json` 后可长期复用，不必提交到公开仓库。

状态有三种：

- `needs_answers`：有必须回答的可达问题，`intakeIntent=null`。
- `needs_transcript`：选择了语音精修，但没有对齐转录，暂不能准备剪辑。
- `ready_for_planning`：偏好约束齐全，可以准备后续规划；仍然不是可执行的 `edit-plan.json`。

每个决策记录 `source=project/profile` 与 `confirmed=true`。段策略中的 `allowBrollSearchOrDownload=false` 是后续素材 adapter 必须遵守的约束。所有输出都固定 `executionPlan=null`、`productionAdaptersReady=false`，避免问询原型被误用成已接好的生产系统。

## 本地试跑

从项目根目录运行：

```powershell
python plugins/jed-video-system/scripts/intake.py --audit plugins/jed-video-system/examples/audit-mixed.json --profile config/user-preferences.example.json
```

这条命令会列出尚未回答的口播 B-roll、录屏标注、语音精修、音效问题，录屏 B-roll 已由明确用户偏好解决。追加 `--answers plugins/jed-video-system/examples/project-answers.json` 后得到可供下一步规划的约束。CLI 不修改草稿，不联网，不下载素材；默认只打印 JSON。未回答退出 2，输入错误退出 1，约束就绪退出 0。

已运行生成两份输出：`examples/intake-pending-no-profile.json` 会问录屏 B-roll，`examples/intake-pending-with-profile.json` 复用用户偏好后不重复问。两者仍为 pending，不能把示例项目答案当成本次客户已确认的剪辑意见。当前本机 `config/user-preferences.json` 只记录录屏 B-roll 为 false 这一条，其他选择未写入。

以 `python -m unittest discover -s tests -p 'intake*_test.py' -v` 运行行为验证。
