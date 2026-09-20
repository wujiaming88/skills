---
name: doubao-seedream-5
description: 使用火山方舟官方 Seedream 5.0 Pro API 进行文生图、图生图与图片编辑。适用于多图参考融合、文字海报、坐标局部编辑、透明图编辑和图层拆分；根据创作意图选择参数并交付图片。
---

# Doubao Seedream 5

模型固定为 `doubao-seedream-5-0-pro-260628`，密钥只读取 `SEEDREAM_API_KEY`。使用官方 `POST https://ark.cn-beijing.volces.com/api/v3/images/generations` JSON 协议。文生图、图生图和图层拆分均使用这个端点。

## 理解意图并选择模式

从用户需求提取用途、主体、构图/比例、风格、准确文字、参考图分工，以及需要修改和保持的部分。缺少影响结果的关键信息才澄清；其余采用合理默认值并简短说明。

| 用户意图 | 模式与选择 |
|---|---|
| 从文字创作图片、海报、插画 | `generate`；默认 2K、standard；在 prompt 中说明比例及画面内容 |
| 编辑现有图片或融合参考素材 | `edit`；1–10 张图，严格保持图号与输入顺序，写清每张图提供什么 |
| 指定位置改物体、跨图移动主体 | `edit`；标注图或 prompt 内 `<point>` / `<bbox>`，见提示词指南 |
| 修改带透明通道的素材并保留透明背景 | `edit --background transparent`；单张已有透明通道的参考图，输出 PNG |
| 把设计稿拆成可编辑底图与元素 | `layers`；单张 PNG/JPEG，可省略 prompt 自动拆分，默认 size=auto |

阅读 [意图与提示词指南](references/intent-and-prompts.md) 处理文字排版、多图、坐标与图层场景。需要精确尺寸、完整 JSON 或排查参数冲突时阅读 [API 能力与约束](references/api.md)。[命令示例](references/examples.md) 提供可直接调整的调用方式。

能力按需使用：质量优先选 `standard`；用户明确要求更快时选 `fast`。默认保留水印，按用户需求通过 `--no-watermark` 关闭。JPEG适合照片；PNG适合透明素材和需要无损交付的设计稿。不为“利用能力”添加与需求无关的参数。

## 调用

脚本独立运行，需要 Python 3.10+ 和 Pillow；`uv` 是可选的依赖管理工具。脚本路径相对于本 SKILL.md 所在目录解析，输出使用用户工作目录的绝对路径。

运行前先检查环境，选择可用方式：

- 有 `uv`：可使用 `uv run --with Pillow python`；本地 HEIC/HEIF 另加 `--with pillow-heif`。
- 没有 `uv`：查找并验证 `python3` / `python`（Windows 也可用 `py -3`）。已有 Python 3.10+ 且可导入 `PIL` 时直接运行；缺少 Pillow 时，在已有虚拟环境安装，或先在工作目录用 `python -m venv` 创建专用环境。具体命令见[无 uv 的运行步骤](references/examples.md#运行环境uv-可选)。无需为运行此 Skill 专门安装 uv。
- 用选定的解释器执行 `--dry-run` 成功后，再发真实请求。若 Python 版本、venv、pip 或依赖安装失败，明确报告具体原因；不要向系统 Python 强制安装依赖或使用 `--break-system-packages`。

下面的 `<PYTHON>` 替换为已验证、可导入 Pillow 的 Python 可执行文件路径；使用 uv 时，将 `"<PYTHON>"` 替换为 `uv run --with Pillow python`。

```bash
"<PYTHON>" "<SKILL_DIR>/scripts/seedream.py" generate \
  --prompt '一张横向16:9的产品摄影，白色陶瓷杯，柔和侧光，浅灰背景' \
  --size 2K --out /absolute/path/output/seedream-cup
```

`--image` 可重复传入本地路径、公开 URL 或 Data URI；本地文件按原始字节编码，不自动压缩或转码。`--request /absolute/request.json` 接受全部已支持的官方字段，不与生成参数混用。先用 `--dry-run` 校验复杂请求：不联网、无需密钥、不暴露 Base64。URL 输入的格式、尺寸、透明通道及可达性由服务端验证；需要本地确认时先取得用户授权使用的原图并检查。

用户已要求生成或编辑时，可在其范围内执行，不重复索要确认。密钥缺失时提示在本地设置 `SEEDREAM_API_KEY`；不要求用户把密钥发到对话中，不回退到其他环境变量，不写进代码、命令参数或文件。

## 交付和恢复

生成是同步请求，脚本保存 `response.json`、`request-preview.json`、所有图片及 `manifest.json`。使用全新输出目录，避免覆盖。只有 CLI 返回0、`manifest.complete=true` 且真实图片文件可解码时，才报告技术交付成功。继续查看实际图片，核对主体、文字、构图和透明背景；接口成功不代表创作效果符合需求。

图片在Codex中用绝对路径Markdown图片语法展示。拆图交付底图、全部PNG图层及元数据，不能只取 `data[0]`。还原方式：按 `z_index` 升序，将各图层缩放为 `bounding_box.absolute` 的宽高，再叠加到该位置；图层文件原生尺寸可能不同。

URL有效期24小时，及时下载。部分下载失败时说明已保存数量和失败原因，使用 `download --response .../response.json --out <全新目录>` 恢复；无需密钥或重新生成。响应可能含提示词、签名图片URL或Base64，作为用户私有产物保存，不提交到仓库。

生成超时或连接中断时，服务端结果可能未知，禁止自动重发付费POST。该接口没有异步任务查询/取消协议；不要沿用Seedance的任务ID逻辑。先说明状态和已有证据，再决定是否需要一次新的生成。

## 模型边界

- Pro普通请求一次生成一张图；不支持组图、`n`、联网搜索或流式返回。多个候选图需要独立请求，并按用户要求的数量控制调用。
- 透明模式要求单张已有透明通道的输入；不能解释成文生透明图或JPEG自动抠图。
- 没有 `/images/edits`、multipart、mask、seed、quality、strength 或 negative_prompt 字段。负向约束、风格和局部操作写进自然语言prompt。
- 仅支持1K/1.5K/2K或受约束的精确尺寸；不要从其他Seedream型号复制4K、组图或搜索能力。
