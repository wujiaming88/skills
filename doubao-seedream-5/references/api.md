# 官方 API 对照

核对日期：2026-09-20。API文档更新日期：2026-09-09。仅针对 `doubao-seedream-5-0-pro-260628`。

来源：[图片生成API](https://console.volcengine.com/ark/region:cn-beijing/docs/82379/1541523)、[Pro教程](https://ark.volcengine.com/region:cn-beijing/docs/82379/2582774?lang=zh)、[Pro交互编辑指南](https://ark.volcengine.com/region:cn-beijing/docs/82379/2582775?lang=zh)。

## 请求协议

`POST https://ark.cn-beijing.volces.com/api/v3/images/generations`

头部为 `Authorization: Bearer <SEEDREAM_API_KEY>`、`Content-Type: application/json`。CLI不允许覆盖端点或模型，不自动重试POST。

| 字段 | 支持的值与含义 | CLI |
|---|---|---|
| model | 固定 doubao-seedream-5-0-pro-260628 | 自动填入，拒绝其他值 |
| prompt | 普通生成/编辑必填；拆图可省略；建议中文≤300字、英文≤600词，非硬性截断限制 | --prompt |
| image | 单个字符串或数组；公开URL / data:image/小写格式;base64,... | --image，可重复 |
| layer_decomposition | boolean，默认false；true返回底图与最多16个透明层 | layers命令置true |
| size | 普通默认2K；拆图默认auto，详见下表 | --size |
| optimize_prompt_options | {"mode":"standard"}默认；或{"mode":"fast"}降低等待时间 | --optimize |
| output_format | jpeg默认 / png；拆图只控制底图格式，图层固定PNG | --output-format |
| background | opaque默认 / transparent；透明须单张带透明通道输入，默认PNG，与JPEG输出冲突 | --background |
| response_format | url默认，24小时有效 / b64_json | --response-format |
| watermark | boolean，默认true，右下角“AI 生成”水印 | --watermark / --no-watermark |

完整JSON使用 `--request`；仍校验模式和所有字段，未知字段直接拒绝。Pro不支持 `sequential_image_generation`（包括disabled）、`sequential_image_generation_options`、`tools` 或 `stream`。

`watermark=false` 控制本次是否添加水印，不保证消除参考图中已有的水印。2026-09-20实测：图生图关闭水印后，输入海报已有的水印仍被保留；无水印参考素材的输出未出现新增水印。

## 尺寸

| 模式 | 可选值 | 约束 |
|---|---|---|
| 普通生成/编辑 | 1K、1.5K、2K、WIDTHxHEIGHT | 精确像素总数921600–4624220；宽高比1/16–16 |
| 图层拆分 | auto、1K、1.5K、2K | 不接受精确尺寸；底图保持输入比例 |

普通模式按官方建议采用“档位 + prompt比例描述”，需要确切尺寸时指定WIDTHxHEIGHT。档位示例（不是完整列表或比例保证）：

| 档位 | 1:1 | 16:9 | 9:16 |
|---|---|---|---|
| 1K | 1024×1024 | 1424×800 | 800×1424 |
| 1.5K | 1536×1536 | 2048×1152 | 1152×2048 |
| 2K | 2048×2048 | 2816×1584 | 1584×2816 |

文档标注1.5K与1K同价；可优先考虑1.5K质量，不据此编造具体费用。

## 输入图片

| 模式 | 数量 | 格式 | 每图限制 |
|---|---|---|---|
| 文生图 | 0 | — | — |
| 图生图/多图参考 | 1–10 | JPEG、PNG、WebP、BMP、TIFF、GIF、HEIC、HEIF | ≤30MB；宽高均>14；像素196–36000000；比例1/16–16 |
| 拆图 | 1 | JPEG、PNG | ≤30MB；像素262144–36000000；比例1/16–16 |

透明模式进一步要求单图已有透明通道；不接受JPEG输入。脚本检查本地文件和Data URI的真实解码结果；URL原样交给服务端，不假称已检查。HEIC/HEIF本地解码需要可选 `pillow-heif` 插件，安装后自动注册。所有本地图保持原始内容，调整尺寸或转码需明确作为额外处理。

## 响应与完整性

响应包含 `model`、`created`、`data[]`、`usage`。保留完整JSON及未知字段，不把HTTP200当作业务成功。普通响应一张图片；拆图包含底图及所有图层。

| 字段 | 含义 |
|---|---|
| url / b64_json | 可下载URL或Base64图片内容 |
| size、output_format | 实际尺寸与格式；脚本对照真实文件校验 |
| z_index | 底图为0，图层从1开始，较大值覆盖较小值 |
| bounding_box.absolute | [left, top, right, bottom]，相对于输出底图画布的像素坐标 |
| bounding_box.normalized | 同上顺序，相对输出底图归一化到0–1000 |
| name、description | 图层名称和说明，保存为元数据，不作为文件路径 |
| usage | input_images、generated_images、output_tokens、total_tokens；原样保留 |

图层恢复先缩放到 `(right-left, bottom-top)`，再在 `(left,top)` 叠加。不能把图层原图尺寸当成画布展示尺寸。

拆图会生成独立元素并补全遮挡区域，不保证按层重组后与输入逐像素一致。实测中杯碟的补全部分、阴影和背景细节发生变化；交付前仍应查看底图、各层及重组效果。

服务端拆图中任意图层失败，整个请求报错，没有部分服务端成功语义。本地下载可以部分完成：`manifest.complete=false`、非零退出码，原响应和完成文件仍保留，使用download恢复。

脚本本地保护值：JSON响应/文件最大512MB、单个输出文件最大64MB，不是官方输出规格。认证请求禁止重定向；下载仅接受HTTPS，可跟随HTTPS重定向，不携带API密钥。网络操作默认超时300秒，可用 `--timeout` 调整。请求只尝试一次，恢复下载也不创建生成请求。
