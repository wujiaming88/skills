# 官方 API 能力与参数

核对日期：2026-09-18。以下范围为固定模型 `doubao-seedance-2-5-260628`，不把同一通用 API 上的其他模型能力当作 2.5 能力。

## 官方来源

- [用户指定的模型详情](https://console.volcengine.com/ark/region:cn-beijing/model/detail?name=doubao-seedance-2-5)
- [2.5 教程与任务类型规则](https://www.volcengine.com/docs/82379/2607688)
- [2.5 提示词指南](https://www.volcengine.com/docs/82379/2607689)
- [联网搜索使用限制与示例（2.5 教程引用此节）](https://www.volcengine.com/docs/82379/2291680#c40ed3ef)
- [创建任务（用户补充的控制台入口）](https://console.volcengine.com/ark/region:cn-beijing/docs/82379/1520757)，[同文公开文档](https://www.volcengine.com/docs/82379/1520757)
- [查询任务](https://www.volcengine.com/docs/82379/1521309)
- [查询任务列表](https://www.volcengine.com/docs/82379/1521675)
- [取消或删除任务](https://www.volcengine.com/docs/82379/1521720)
- [Base URL 与认证](https://www.volcengine.com/docs/82379/1298459)
- [肖像素材的合法输入路径](https://www.volcengine.com/docs/82379/2608626)

未来文档变更时先复核上述来源，再更新校验；不要通过修改固定模型或盲目放开未知字段规避错误。

## 认证与协议

根地址：`https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks`。

认证头：`Authorization: Bearer <环境变量中的值>`；请求头：`Content-Type: application/json`。CLI 只从 `SEEDANCE_API_KEY` 读取，禁止认证请求重定向，不向产物下载地址转发认证头。

推荐由密钥管理器或运行环境注入 `SEEDANCE_API_KEY`；需要手动运行时，下面示例通过隐藏输入只给子进程传递密钥，不在命令参数或历史中出现密钥：

```python
import getpass
import os
import subprocess
import sys

child_env = os.environ.copy()
child_env["SEEDANCE_API_KEY"] = getpass.getpass("Seedance API key: ")
subprocess.run(
    [sys.executable, "/absolute/path/to/doubao-seedance2.5/scripts/seedance.py",
     "create", "--request", "request.json", "--wait", "--out", "video.mp4"],
    env=child_env,
    check=True,
)
```

这段配置在用户本地终端执行；不要让用户把密钥发到聊天中。子进程环境不会自动配置未来的 Agent 会话。

| 操作 | HTTP | CLI | 语义 |
|---|---|---|---|
| 创建 | `POST /tasks` | `create` | 异步返回 `id`，不是视频完成 |
| 查询 | `GET /tasks/{id}` | `get` | 返回完整状态、产物、用量、错误 |
| 列表 | `GET /tasks?...` | `list` | 分页、筛选、完整 items/total |
| 取消/删除 | `DELETE /tasks/{id}` | `delete` | queued 取消；succeeded/failed/expired 删除记录 |
| 等待 | 重复查询 | `wait`、`create --wait` | 终态退出，默认最多等待 600 秒、间隔 10 秒 |
| 下载 | 查询后 GET 产物 URL | `download`、`create --out` | HTTPS 流式下载；无 Bearer；不完整或格式不符不发布文件 |

CLI 不自动重试请求，尤其不重试可能重复计费的 POST。HTTP 超时默认 60 秒，可用 `--http-timeout` 调整。任务 ID 会在创建后立即输出到 stderr；`--receipt` 另将初始响应落盘，即使后续等待失败也能恢复。

## 创建请求字段全集

`--request` 文件使用官方 JSON 结构；未提供 `model` 时脚本补入固定值，传其他值直接拒绝。标记“默认”均为官方 API 默认；Agent 的一般创作默认值见 SKILL.md。

| 字段 | 类型、默认与范围 | CLI / 用途 |
|---|---|---|
| `model` | string，固定模型 | 自动设置，无覆盖开关 |
| `content` | 非空 object[]，具体类型见下表 | 素材开关或完整 JSON |
| `omni_reference_task_type` | `auto`（默认）、`reference`、`edit`、`extend` | `--omni-reference-task-type`；仅全模态参考场景 |
| `resolution` | `480p`、`720p`（默认）、`1080p` | `--resolution`；不支持 4k 输出 |
| `ratio` | `16:9`、`4:3`、`1:1`、`3:4`、`9:16`、`21:9`、`adaptive`（默认） | `--ratio`；首尾帧、编辑、延长仅 adaptive |
| `duration` | integer，`-1`（默认）或 `[4,30]` 秒 | `--duration`；编辑只能 -1 |
| `generate_audio` | boolean，默认 true | `--generate-audio` / `--no-generate-audio`；有声输出为单声道 |
| `watermark` | boolean，默认 false | `--watermark` / `--no-watermark`；右下角 AI 生成标记 |
| `output_format` | `mp4`（默认）或 `mov` | `--output-format` |
| `return_last_frame` | boolean，默认 false | `--return-last-frame` / `--no-return-last-frame`；返回尾帧 URL；文档标注 PNG，2026-09-18 实测实际内容为 JPEG，下载以签名为准 |
| `callback_url` | string，公网 HTTP(S) 回调地址 | `--callback-url` |
| `execution_expires_after` | integer，`[3600,259200]`，默认 172800 秒 | `--execution-expires-after`；从 created_at 起算的服务端过期时间 |
| `priority` | integer，`[0,9]`，默认 0 | `--priority`；同一 Endpoint 内数值越大排队越靠前，不抢占运行任务 |
| `safety_identifier` | string，英文标识，最多 64 字符 | `--safety-identifier`；使用稳定哈希，避免原始个人信息 |
| `tools` | object[]，支持 `{"type":"web_search"}` | `--web-search`；仅纯文本输入，启用不保证实际搜索，查看 usage |
| `service_tier` | 2.5 仅在线 default；不支持 flex | 可在 JSON 显式传 default；通常省略，不宣称具有可选服务等级能力 |

`content` 元素：

| 类型 | 官方 JSON | 输入方式 / CLI |
|---|---|---|
| 文本 | `{"type":"text","text":"提示词"}` | `--prompt` 或 `--prompt-file`；有其他素材时可省略文本 |
| 图片 | `{"type":"image_url","image_url":{"url":"..."},"role":"reference_image"}` | 公网 URL、Data URI、`asset://ID`；本地文件由 CLI 编码 |
| 首/尾帧 | 同图片，role 为 `first_frame` / `last_frame` | `--first-frame`、`--last-frame`；单首帧的 role 可省略，CLI 总是显式传入 |
| 参考图 | role 为 `reference_image`，必须显式填写 | 可重复 `--reference-image` |
| 视频 | `{"type":"video_url","video_url":{"url":"..."},"role":"reference_video"}` | 公网 URL、`asset://ID`；可重复 `--reference-video`；不接受视频 Base64 |
| 音频 | `{"type":"audio_url","audio_url":{"url":"..."},"role":"reference_audio"}` | 公网 URL、Data URI、`asset://ID`；可重复 `--reference-audio`；允许只输入音频 |

CLI 按文本、首帧、尾帧、参考图片、参考视频、参考音频排列，各类型内部保留命令行重复顺序；`--request` 完整保留数组顺序。模型素材编号应与各类型实际顺序一致。图片默认角色是首帧，不能用多个无 role 图片代替参考图。

Data URI：`data:image/png;base64,...`、`data:audio/wav;base64,...`。不将本地路径直接写到官方 `url` 字段；完整 JSON 不自动把路径转换为 URL。

## 素材与输出限制

| 项目 | 限制 |
|---|---|
| 素材总数 | 最多 30 图 + 10 视频 + 10 音频 = 50；各类独立计数 |
| 图片 | jpeg/png/webp/bmp/tiff/gif/heic/heif；单张 <30 MB；宽/高均 300–6000 px；宽高比 0.4–2.5 |
| 视频 | mp4/mov；单个 ≤200 MB；非编辑 2–30 秒，编辑 4–30 秒；所有参考视频合计 ≤30 秒；24–60 fps |
| 视频像素 | 宽/高均 300–6000 px；宽高比 0.4–2.5；像素积 407696–8295044 |
| 视频编码 | H.264/AVC、H.265/HEVC；mp4 音频 AAC/MP3；mov 另支持 PCM |
| 音频 | wav/mp3；单个 ≤15 MB；单段 2–30 秒；所有参考音频合计 ≤30 秒 |
| 请求体 | ≤64 MB；脚本按 64 MiB 限制编码后 JSON，Base64 会扩大体积，接近上限时优先 URL |
| 输出 | 480p/720p/1080p，24 fps，4–30 秒（编辑可能非整数秒）；mp4/mov |

公开创建 API 的视频输入分辨率列出 480p/720p/1080p/4k，而 2.5 教程仍只列 480p/720p，存在文档差异。CLI 不因此屏蔽高分辨率视频 URL；优先使用满足尺寸、像素积限制的素材，高分辨率支持以实际服务端校验为准。脚本不下载参考 URL 进行探测，也不保证远端素材满足时长、编码、尺寸和肖像限制。

官方创建 API 把 `frames`、`seed`、`camera_fixed`、`draft` 和 `draft_task` 限定于其他模型；2.5 不支持 `service_tier=flex`。这些参数不通过弱校验提示词偷偷传入。没有独立的 `fps`、`negative_prompt`、`language`、编辑时间段、延长方向字段；相应创作要求写入提示词。

1080p 产物采用 10bit 与 H.265/HEVC；mov 面向专业后期，官方描述其采用 H.264+yuv444p+PCM。不要仅凭扩展名保证所有播放器可用，实际编码以产物探测为准。编辑输出时长可能略短于输入；`duration` 查询值是总帧数 /24 向下取整，不是精确小数时长。

## 查询、列表与删除

列表全部查询参数：

| Query 参数 | CLI | 范围与注意事项 |
|---|---|---|
| `page_num` | `--page-num` | 1–500，默认 1 |
| `page_size` | `--page-size` | 1–500，默认 20 |
| `filter.status` | `--status` | 官方列出 queued/running/cancelled/succeeded/failed；文档未列 expired 筛选值，查询过期任务用 ID 或不筛选 |
| `filter.model` | `--endpoint-id` | 官方定义是 ep- 推理接入点 ID，不是固定 Model ID；不默认传模型字符串 |
| `filter.service_tier` | `--service-tier` | default/flex；这是通用任务列表筛选，2.5 创建不支持 flex |
| `filter.task_ids` | 可重复 `--task-id` | 重复 query key，非逗号拼接，非 JSON 数组字符串 |

列表可能包含账号的其他模型任务；固定模型约束作用于创建。查找当前任务优先使用已保存 ID，不把缺少 filter.model 当成只查 2.5。

创建响应：`{"id":"..."}`。查询响应完整保留：`id`、`model`、`status`、`content.video_url`、`content.last_frame_url`、`error.code/message`、`created_at`、`updated_at`、`duration`、`framespersecond`、`resolution`、`ratio`、`output_format`、`generate_audio`、`execution_expires_after`、`safety_identifier`、`service_tier`、`tools`、`usage`。通用接口若返回 `seed/frames/draft/draft_task_id` 也原样保留，不将返回字段视为 2.5 可配置参数。

`usage.completion_tokens`、`usage.total_tokens` 用于记录消耗；`usage.tool_usage.web_search` 是实际搜索次数，0 表示未搜索。没有实际价格和计费结果时不自行把 token 换算为准确费用。列表返回 `items`（同查询结构）和 `total`。

状态：`queued → running → succeeded/failed/expired`；queued 可被取消为 `cancelled`。`wait/create --wait` 对失败、取消、过期返回 JSON 并以退出码 1 结束；get/list 为诊断命令，HTTP 成功即可退出 0，需自行查看 status。未知状态失败退出。HTTP/参数/下载错误退出 1，本地 Ctrl-C 退出 130。

实测补充（2026-09-18）：4 秒普通生成返回 97 帧、实际约 4.042 秒；4 秒延长返回 96 帧、实际 4 秒，输出是新增片段。编辑/延长的 `ratio=adaptive` 响应可为实际像素比例 `427:240`，不局限于请求的预设比例枚举。调用方应保留原始返回值。

DELETE：queued 变 cancelled；succeeded/failed/expired 删除任务记录；running/cancelled 不支持。成功 HTTP 200，官方描述 `Result` 为空对象；CLI 保留响应，同时兼容空响应体。DELETE 的成功响应不冒充视频生成成功。

## 回调与恢复

`callback_url` 的 POST body 与查询响应相同，涵盖 queued/running/succeeded/failed/expired。官方说明 succeeded/failed 通知若 5 秒内未收到成功响应会回调三次；接收端应按任务 ID 和状态幂等处理，快速应答。CLI 不搭建回调服务器；关键终态用鉴权 get 复核，避免信任伪造通知。

任务记录保存 7 天；产物 URL 有效期 24 小时且最多下载 100 次。取消记录 24 小时后自动删除。网络错误保留 ID 与回执，恢复 wait/download；429、5xx、异步参数错误要先诊断，只有确认需要新生成且仍在用户授权范围内才再次创建。

企业/个人的创建限额和并发数可能变化，应查教程或控制台。当前教程列出非推理接口账号上限：查询 20 QPS，列表 1 QPS，删除 20 QPS；默认 10 秒轮询不会逼近该上限。
