# Jed Video System 插件原型 0.2

采用本机已安装剪映插件的真实包格式：`plugins/jed-video-system/.codex-plugin/plugin.json`，skills 指向 `./skills/`。本轮只是工作区内的可审查插件包，尚未安装进全局插件目录，也没有创建公共仓库。

客户问询与时间编译器使用标准库；转录复用本机 Video Use / WhisperX，视觉复用 Remotion，草稿复用固定 fork 与 Bridge。已由同一人工计划产出原声预览、独立透明动效与可编辑新草稿。仍依赖绑定的工作区，尚未成为脱离本机环境的通用安装包。

## 分模块的责任

| 模块 | 本版状态 | 后续接口边界 |
| --- | --- | --- |
| Intake | **implemented** | audited segments + project answers + explicit profile → questions / planning constraints |
| Brand / Motion | 已选A与真实视频共用透明层 | 固定组件、内容props、无深色底 |
| Plan compiler | **implemented** | 原秒时间、anchor词ID → 统一帧时间；仅1倍速 |
| Remotion adapter | **implemented-pilot** | 同一props → 原声预览与独立Alpha，不接管草稿 |
| Talking-head edit | 约束与时间映射已实现 | 停顿/重复句候选审核尚未接入；本轮完整保留讲述 |
| Video Use adapter | **implemented-local-transcription** | 内容、配置、helper和runtime版本共同管理缓存 |
| Jianying CLI / Bridge | **implemented-probe** | 音效副本、验证、首页事务通过；原CLI未新增通用视频命令 |
| Jianying MCP | 外部服务，当前入口配置缺项 | 缺JY_INSTALL_DIR；显式Bridge可读，不复制服务 |
| Jianying draft adapter | 结构与发布通过，UI待验证 | 一个底片、一个覆层、逐条可编辑字幕；不改正式旧工程 |
| Sound design adapter | **stub** | 复用已有 Skill 的声音经验与 CLI 素材解析；不再建一套音效引擎 |

机器可读登记在 `adapters/registry.json`。`stub` 只有状态说明，没有装作可运行的假函数。插件本身目前不声明 `mcpServers`，所以不会重复启动已安装的 `jianying-local`。未来完整安装包若需要统一入口，可指向同一现有 Bridge runtime，而不是复制服务实现；Remotion 也以现有库与入口接入，不把第三方插件整个嵌套进新插件目录。

## 本地配置与公共代码

公共 `config/local.example.json` 只给字段，真实路径放未提交的 `config/local.json`。剪映优先引用现有 `%LOCALAPPDATA%/jianying-mcp/runtime.json`；其中 Python、entry、config 由已安装工具维护。不要在公共 manifest 写本机绝对路径、账号令牌或重写第三方 runtime。示例中的 `<LOCALAPPDATA>` 是配置占位符，本轮没有 adapter 去展开或执行它。

明确用户偏好放 `config/user-preferences.json`，每次项目答案单独保存。问询规则只读取两者，不把这次答案自动升级成长期偏好，也不自动改客户配置。

## 下一段的实际接入顺序

已建立 edit-plan Schema 与共享帧props，完成人工计划闭环。下一段补齐剪映应用验收、环境能力检查、MCP环境绑定和失败恢复，再连接客户问询与自动规划。intake退出0只说明约束齐全；`productionAdaptersReady=false` 继续保留，因为本机草稿UI尚未验收，不把试验路径宣告为可自动生产。
