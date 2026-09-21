---
name: doubao-seedance2.5
description: 使用火山方舟官方 Seedance 2.5 API 理解视频创作意图并生成、编辑或延长视频。适用于文生视频、首帧/首尾帧、图片/视频/音频参考、音画同步、多语言对白、联网搜索，以及生成任务的查询、下载、取消和删除。模型固定为 doubao-seedance-2-5-260628，密钥仅从 SEEDANCE_API_KEY 环境变量读取。
---

# Doubao Seedance 2.5

将用户意图转换为官方 `contents/generations/tasks` 请求，用本 Skill 的 CLI 执行并交付视频。Python 3.10+，仅使用标准库，无需 SDK。`{baseDir}` 指本 Skill 目录。

## 固定配置

- 模型：`doubao-seedance-2-5-260628`，不切换模型或 Endpoint ID。
- API：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`。
- 密钥：只读 `os.environ["SEEDANCE_API_KEY"]`，不接受密钥命令行参数、JSON 字段或其他环境变量回退。不打印密钥、不写入仓库或回执。
- 通过宿主进程或密钥管理器注入环境变量；需终端交互配置时，参见 [references/api.md](references/api.md#认证与协议) 的不回显输入示例。
- 本目录名和 frontmatter 按用户要求保留 `2.5`。只允许小写字母、数字、连字符的 Skill 加载器可能不接受点号；遇到该限制需说明，不擅自改名。

## 理解意图

先识别素材职责与任务类型，再选择参数。自然语言理解由使用 Skill 的 Agent 完成；CLI 不用关键词猜测用户意图，也不调用另一个文本模型。

| 用户意图 | 请求映射 | 必须保持的约束 |
|---|---|---|
| 从描述创作新视频 | `content.type=text` | 明确主体、动作、镜头和声音 |
| 让这张图动起来 / 从这一帧开始 | `image_url` + `role=first_frame` | `ratio=adaptive` |
| 从图 A 过渡到图 B，严格控制起止帧 | `first_frame` + `last_frame` | 首尾帧各一张，`ratio=adaptive` |
| 参考人物、产品、动作、风格、故事板或声音创作 | `reference_image/video/audio` + `omni_reference_task_type=reference` | 最多 30 图、10 视频、10 音频；允许只有音频 |
| 修改已有视频画面或声音 | 参考视频 + `omni_reference_task_type=edit` | `ratio=adaptive`，`duration=-1`；在提示词明确编辑目标和保留内容 |
| 向前/向后续写视频 | 参考视频 + `omni_reference_task_type=extend` | `ratio=adaptive`；明确方向、目标素材和时长含义 |
| 混合意图，无法可靠区分参考/编辑/延长 | `omni_reference_task_type=auto` | 通常用 `ratio=adaptive`、`duration=-1`；告知自动时长可能为 4–30 秒 |
| 查询、下载、取消、删除已有任务 | `get/list/wait/download/delete` | 不重新创建生成任务 |

严格首尾帧模式不能混用任何参考图片、视频或音频。若用户既要严格首尾帧又要其他参考，说明约束并确认优先目标；普通关键帧参考可用 `reference_image`，但不承诺像素一致。

同时命中多种意图时，先按硬约束过滤，再向用户确认优先目标，不静默挑一种执行。

素材角色不明、待编辑视频不明，或请求与模型硬限制冲突时，只问影响执行的必要问题：只问 1–2 个影响执行路径、素材引用、交付范围或事实准确性的问题，用选择题；关键信息缺 1 项按默认值直接执行，缺 2 项及以上必须先澄清；澄清最多 1 轮；用户说“你来定”“直接生成”时跳过。

参数默认值直接生效：未指定的一般创作采用 **720p、5 秒、有声、mp4**，画幅按用途选择（竖屏 `9:16`、横屏 `16:9`；受锁定的任务用 `adaptive`）。交付时说明这些取值来自默认推断，供用户按需调整，不为参数推断单独增设确认环节。不要把 5 秒默认值套入编辑任务；编辑必须 `-1`。1080p 画质更高、成本更高；编辑/延长建议 mov，交付平台要求 mp4 时按要求使用。

复杂分镜、多素材、多语言、编辑/延长任务先读 [references/intent-and-prompts.md](references/intent-and-prompts.md)。参数全集、素材限制、返回字段和官方依据见 [references/api.md](references/api.md)。常见完整请求见 [references/examples.md](references/examples.md)。

## 执行

1. 保留用户具体创意、台词与约束；素材按各类型输入顺序编号为 `@图片1`、`@视频1`、`@音频1`。不把多张参考图误当首尾帧。
2. 根据意图组装官方 JSON 或 CLI 参数。参数写入 JSON 字段，不在提示词后追加弱校验的 `--dur` 等控制串。
3. 新请求先 `--dry-run`，检查模式、素材角色、时长和画幅；它不联网、不需要密钥、不代表生成成功。Data URI 预览会省略 Base64，不可将预览当完整请求重放。
4. 用户已要求生成时，直接提交其授权范围内的一次请求。仅写提示词、编写 Skill 或演示命令不代表授权实际生成。不自动重复付费请求；创建超时或缺少 ID 时先核对列表。
5. 创建后立即保留任务 ID；需交付视频时等待终态并下载。建议使用 `--receipt` 保存创建结果和最终状态。轮询使用同一个任务 ID；本地等待超时或中断不取消远端任务。
6. 确认 `status=succeeded`、产物已下载且文件非空。CLI 检查容器签名和传输长度；尾帧 URL 后缀可能与实际格式不同，2026-09-18 实测 `.png` URL 返回 JPEG。按实际格式使用 `.jpg` 或 `.png` 输出路径，格式不符时只重试尾帧下载。若有 `ffprobe`，检查真实时长、尺寸、帧率和音轨，播放抽查开头/中间/结尾、动作连贯性、音画与台词。不把签名检查称为画面质量验证。
7. 交付本地视频、最终提示词/请求文件、任务 ID、实际规格和可用的 token/搜索用量。支持本地媒体预览的环境直接展示；否则给文件链接。描述未完成或失败状态，不宣称已生成。

基本创作：

```bash
python3 {baseDir}/scripts/seedance.py create \
  --prompt "写实微距镜头，一朵花在晨光中缓缓绽放，镜头轻推，伴随鸟鸣，无对白" \
  --resolution 720p --ratio 16:9 --duration 5 --dry-run

python3 {baseDir}/scripts/seedance.py create \
  --prompt "写实微距镜头，一朵花在晨光中缓缓绽放，镜头轻推，伴随鸟鸣，无对白" \
  --resolution 720p --ratio 16:9 --duration 5 \
  --wait --receipt output/seedance/flower-task.json --out output/seedance/flower.mp4
```

完整 JSON 使用 `create --request request.json`，不能与生成参数混用；`--wait`、`--receipt`、`--out` 等本地执行选项可组合。本地图片和音频可通过素材参数自动编码；本地视频应先上传到用户已指定的存储后传 URL，CLI 不自建存储、不隐式上传。

任务操作：

```bash
python3 {baseDir}/scripts/seedance.py get TASK_ID
python3 {baseDir}/scripts/seedance.py wait TASK_ID --wait-timeout 600 --poll-interval 10
python3 {baseDir}/scripts/seedance.py list --status succeeded --page-num 1 --page-size 20
python3 {baseDir}/scripts/seedance.py download TASK_ID --out output/seedance/video.mp4
python3 {baseDir}/scripts/seedance.py delete TASK_ID
```

只在用户要求取消/删除时用 `delete`：排队任务取消，成功/失败/过期任务删除记录；运行中任务不能取消。删除记录后不能再查询，先下载用户需要的产物。默认不覆盖文件，明确替换时才用 `--force`。

## 能力边界与失败恢复

- 覆盖固定模型当前支持的全部生成请求字段，以及创建、查询、分页筛选、取消/删除四类任务 API；保留完整查询响应，不丢弃用量、错误或返回元数据。
- 不支持 4K 输出、任意帧率、`frames`、`seed`、`camera_fixed`、`draft/draft_task`、`service_tier=flex`；静止镜头和多语言通过提示词表达，没有独立 `fps`、`language`、`negative_prompt` 参数。模型页曾显示“样片模式”标签，但创建 API 明确将其限定于 1.5 pro，以 API 的模型适用表为准。
- `omni_reference_task_type` 只帮助前置校验，模型仍会理解提示词；模式与提示词矛盾可异步返回 `InvalidParameter.TaskTypeMismatch`。修改请求之前读取 `error.code/message`，避免盲目重复提交。
- 联网搜索仅适用于纯文本输入，不能与图片、视频或音频参考组合；`tools=[{"type":"web_search"}]` 不保证实际执行搜索，须检查 `usage.tool_usage.web_search`。需要事实准确性时，搜索次数为 0 的结果不能当作已联网核验。
- 请求体上限 64 MiB；图像、音视频数量由 CLI 校验，公网素材的时长、尺寸、编码和可达性仍需核对并由服务端最终校验。不要声称 dry-run 已验证这些媒体属性。
- URL 有效期 24 小时，任务保留 7 天，2.5 产物 URL 最多下载 100 次。下载失败使用原任务 ID 重试下载；过期 URL 不保证能通过 get 刷新。
- 回调仅配置 `callback_url`，不自动部署接收服务。服务端会向该地址 POST 任务状态；没有官方验签约定时不要编造签名算法，可用 get 复核关键终态。
- 官方不支持直接输入普通真人人脸图/视频；涉及肖像时使用官方认可的已授权素材/人像库或符合条件的本账号原始生成产物，参见 API 参考中的官方肖像指南，不改用编码方式绕过限制。
