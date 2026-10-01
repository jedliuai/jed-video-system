# 章节独立停顿与短音效

本文记录0.6候选预览阶段。0.7已把插入版接到剪映11轨新工程并登记首页，原生图片/文字、透明块和声音分别保留，当前交接见 [editable-chapter-delivery.md](editable-chapter-delivery.md)。下文“尚未接入”描述0.6当时的边界。

0.6按用户新要求，将章节转场改为“说完前一句 → 独立图片动画和短音效 → 接着下一句”。保留已经认可的浅色剪纸、蓝色点缀和1.8秒时长。完整保留原口播，不通过静音或覆盖源片段删除语音。

## 本机已完成的结果

`work/chapter-insert/20261001-r2/sample.mp4`为9.8秒小样，包含转场前2秒与转场后6秒。用户已明确回复“认可这版音效和衔接”，真实回执在 `work/chapters/review-state-insert-r2.json`，candidate为 `chapter-insert-sound-sample-r2`，绑定视频SHA、props、图片、声音、原始媒体、字体和相关实现；递归摘要核验后allowed=true。旧画风确认保留在历史记录中，没有改写旧样片。

完整候选 `work/chapter-insert/20261001-r2/preview.mp4`为1920×1080、30fps、1278帧、H.264/AAC，42.6秒。源片段原长40.8秒，切点位于源第204帧，即6.8秒。章节占输出204–258帧，之后的源第204帧从输出第258帧接回。16条字幕和后续动效一起后移54帧；整片没有新增B-roll。

音效通过现有剪映MCP查询本机缓存获得：“呼”的转场音效。取源音效0.2秒开始的1.1秒，降低9.4dB，加入0.04秒淡入、0.2秒淡出，准备为48kHz立体声WAV。章节开始0.1秒后响起，1.2秒时结束，在口播恢复前留出0.6秒。没有背景音乐，也没有联网下载音效。缓存资源ID和机器路径保存在忽略的work中，声音资产不随公共仓库分发。

音频重建使用原始源样本：前段语音、1.8秒独立静音区间、后段语音按输出顺序拼接，只在插入区间叠加准备好的音效。丢弃Remotion初次编码音轨后，从原源音频重新生成一次AAC，避免沿用连续片段校时逻辑将停顿“纠正掉”。原声6处内部窗口相关性均大于0.9996，时间偏移均0；章节区间与“只有音效”的期望轨相关性约0.99947、偏移0。这些是采样窗口校时证据，不是逐音素、主观试听或剪映播放认证。

新增12项行为检查，共157项通过；Remotion ESLint/TypeScript通过。单切点真实渲染与重复成功job复用已验证；多切点映射通过测试，尚未做多切点完整媒体试验。准备回执保留当时的audioAndPacingApproved=false，后到的真实批准单独存入review state，不篡改原执行回执。

## 输入和调用

从项目根执行，默认仅检查并规划；加 `--execute` 生成新job：

```powershell
python plugins/jed-video-system/scripts/prepare_chapter_insert.py --props work/plans/live-render-props.json --cards work/chapters/insert-r2/cards.json --job-id 20261001-r2 --execute
```

props为未经章节插入的连续单源30fps计划，cards格式见 `schemas/chapter-insert.schema.json`。明确给出句间源帧切点、前后原话、图片、标题、编号、风格版本，以及已处理好的短声音文件和帧区间。host负责核查切点原话和画面，程序不凭文字字段证明它真是句间。

编译器独立维护sourceBoundaryFrame与outputStartFrame，保留源帧连续性并让所有后续事件按同一映射后移；拒绝重复插入、穿过字幕短句或正在播放的动效、声音溢出章节区间、缺失章节卡与声音。没有实现任意变速、重排、精修时间线上的追加插入或通用画幅。

执行记录位于 `work/chapter-insert/<job-id>/`，绑定媒体、输入、字体、渲染实现和运行时摘要，保留日志与产物SHA。不覆盖现有job；同一成功版本可复用，失败或输入变化检查后用新job-id。克隆仓库不会包含这些个人媒体、缓存声音、字体或本机配置，需自行准备合法可用的资产。

校时使用既有Video Use Python环境中的NumPy/SciPy：

```powershell
python scripts/verify-inserted-audio.py --props work/chapter-insert/20261001-r2/props.json --public-root motion-lab/public --candidate work/chapter-insert/20261001-r2/preview.mp4 --output work/chapters/insert-r2/audio-check.json
```

## 确认与交接边界

用户明确要求“转场期间不说话”，这是制作偏好，直接落实，不重复询问是否暂停。画风与时长已有确认，只让用户看新声音和停顿衔接小样；真实回复只覆盖展示版本的音效和节奏，没有泛化为整片接受或其他客户的长期偏好。新的声音处理或不同运动配方重审受影响范围，静态图片不能批准音效。

ChatCut和Remotion官方插件未修改；调用原有本地Remotion运行时。剪映MCP本轮doctor、声音指南、缓存查询均成功，旧安装目录缺项是历史状态，无需再登录或重复启动服务。

本轮完成的是隔离候选预览和插件时间映射。新的42.6秒插入计划尚未接入剪映草稿；原0.5 cover交接保持原实现并明确拒绝新timelineMode。不能将旧四轨40.8秒草稿描述成新版已经交付，剪映应用播放、保存重开和原生导出仍待单独验证。
