# 第二阶段：真实口播转录与时间协议

2026-10-01。这次只复用 Video Use 的本地转录 helper，没有启动它的自由设计流程，没有改第三方 Skill，也没有剪掉原视频或替换声音。

## 已实际完成

根目录 `个人实拍案例.mp4` 的 40.8 秒样片已用已有 WhisperX 3.8.6 环境完成转录。模型为 large-v3-turbo，中文，CUDA float16，batch size 4，单人素材不做说话人分离。RTX 4060 上 ASR 加对齐用时 35.67 秒；helper 采样到峰值显存 3813 MB，基线 1473 MB。这是这一次运行数据，不是速度保证。

实际得到 231 个带时间的字/词。中文对齐模型以字为单位，英文 copy 被分成 c/o/p/y，不能把这个计数理解成 231 个中文词组。原 helper 记录的插值字数为 0；wrapper 对照保留的 raw source_segments，逐字核对后也没有发现插值或调整。强制对齐仍是估计，本阶段没有完成逐字人工试听验收，不能把它当作逐帧真值。

完整标准结果在 `work/transcripts/45f61e99b234111644a768371ed6d21c94b788b65a8eeac8cdf306ee2f45b1c8/transcript.json`。同目录保存原始 helper JSON、helper.log 和 manifest.json。便于动画消费的人工短句索引在 `work/manifests/transcript-cues.json`，阶段汇总在 `work/manifests/transcript-stage.json`。

## 接入方式

入口为插件的 `scripts/transcribe.py`；实现集中在 `src/jed_video_use/`，只用 Python 标准库。它调用本机 `video-use/helpers/transcribe.py`，重型依赖仍在已有专用环境。本机路径可用 CLI 参数覆盖，无需再安装 WhisperX。

缓存键包含源视频文件内容 SHA256、转录配置、transcribe.py 与 whisperx_runner.py 的实际内容哈希、WhisperX / Torch / faster-whisper / CTranslate2 实际版本以及 adapter 格式版本。缓存目录按该键隔离，再让旧 helper 在里面使用 stem 文件名；所以同名不同内容的 clip.mp4 不会混用转录。推理后再次核对源文件哈希，防止执行中换源片。

缓存键目前假定同名本地模型权重不会被原位替换，未对数 GB 权重逐次做哈希。如果更换模型权重，应使用新模型标识或清理对应缓存。本地运行 manifest 记录模型目录与 Python 路径。没有自动 CPU 或付费 ElevenLabs 回退；失败会以非零退出码和 failed manifest 明确报告。

## 原片时间是唯一坐标

`sourceTime.start/end` 都是从这份实际转录输入样片的 0 秒起算；转录源 SHA256 为 `0b88c40281a56637dadc2c9a208c595e21a4ba32a1ccec54e804172c20542348`。它不属于其他 raw 视频。若总控确认与长素材某段匹配，应另外保存“源片映射与核验方法”，不能直接把这里的哈希移到长素材上。

保留 helper 的两个大 ASR 段，另给每个字/词独立 ID、原片时间、置信度、segmentId 和 timingQuality。`forced_aligned` 表示保留了模型对齐边界；`interpolated` 表示原始词没有边界；`helper_adjusted` 表示 helper 为顺序/最短时长修改过；无法可靠映射时用 `unknown`。后三类都明确标 approximateBoundary=true。ASR 大段的边界始终标近似。

标准化会拒绝负数、非有限数、倒置、零长、越过源时长、重叠或乱序的词区间。JSON Schema 描述结构，运行时校验负责 start < end 等跨字段关系。

## 动效应如何读这份转录

- 0.042–2.843 秒：那么完全可以直接去copy我的这个代码。
- 2.843–4.764 秒：大家可以关注或者说私信我。
- 4.764–6.805 秒：我会把原码直接的提供给大家。
- 6.805–10.406 秒：接下来我会去演示一下我这个系统的效果到底是怎样的。
- 10.406–11.947 秒：首先我们来看一下。
- 11.947 秒之后进入打开网站、账号密码与首页讲解。

这里刻意保留“原码”等 ASR 原文。动效卡片可以人工写成“源码”，但应在展示文案里修正，不能假装 ASR 原文已经准确。copy 的分字也一样，展示词组可以合并，底层字级时间保留。

视觉抽样确认口播到录屏切换约在 11.8 秒，抽样区间约 11.7–11.8 秒，按约 ±0.1 秒处理；没有逐帧认定。对应取样见 `work/transcripts/transition-review-fine.jpg`。口播信息元素可在 11.6 秒前退场，录屏沿用用户“不加 B-roll”的偏好。不能仅从“演示”二字就判定画面已切换。

## 验证

`tests/transcript_adapter_test.py` 覆盖同名异内容缓存隔离、配置/helper/运行库变更失效、插值与调整质量标记、非法字级/段级区间、重叠词、未知映射保守标记、helper 失败落盘及 CLI 非零退出。目前 9 项通过；另用真实转录验证成功与缓存复用。没有镜像实现的模拟 ASR 测试，也没有重新装环境。
