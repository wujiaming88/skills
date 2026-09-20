# 调用示例

`<SKILL_DIR>` 替换为本Skill绝对目录。运行前在本地安全设置 `SEEDREAM_API_KEY`，不把值写进示例或仓库。输出目录须尚不存在。

## 运行环境（uv 可选）

先检查 `uv` 是否可用（macOS/Linux：`command -v uv`；PowerShell：`Get-Command uv -ErrorAction SilentlyContinue`）。有 uv 可沿用下文示例；没有 uv 时按以下步骤运行。

**1. 检查已有 Python。** 下例使用 `python3`，也可替换为本机的 `python` 或 Windows 的 `py -3`。先确认版本，再检查 Pillow；成功后输出可直接调用的解释器路径。

```bash
python3 -c "import sys; assert sys.version_info >= (3, 10), '需要 Python 3.10+'; import PIL; print(sys.executable)"
```

**2. 仅在缺少 Pillow 时准备依赖。** 若已有虚拟环境，用该环境的 Python 执行 `-m pip install Pillow`；否则在用户工作目录创建 `.venv-seedream`。以下为 macOS/Linux 命令，无需激活环境：

```bash
python3 -m venv .venv-seedream
.venv-seedream/bin/python -m pip install Pillow
.venv-seedream/bin/python -c "import PIL; print(PIL.__version__)"
```

Windows PowerShell 使用：

```powershell
py -3 -m venv .venv-seedream
.\.venv-seedream\Scripts\python.exe -m pip install Pillow
.\.venv-seedream\Scripts\python.exe -c "import PIL; print(PIL.__version__)"
```

本地 HEIC/HEIF 输入还需在同一环境执行 `-m pip install pillow-heif`。Python 低于 3.10 时先选择符合版本的解释器；缺少 Python、venv/ensurepip 或依赖下载失败时，报告实际错误并给出对应平台的修复步骤，不反复执行失败命令，也不绕过系统 Python 的包管理保护。

**3. 使用该解释器先做 dry-run。** `<PYTHON>` 是第1步输出或第2步创建的解释器路径。此步骤不需要密钥，不调用图片 API：

```bash
"<PYTHON>" "<SKILL_DIR>/scripts/seedream.py" generate --prompt '一只白色陶瓷杯' --dry-run
```

PowerShell 中，带引号的可执行文件路径前需加调用运算符：`& "<PYTHON>" "<SKILL_DIR>/scripts/seedream.py" generate --prompt '一只白色陶瓷杯' --dry-run`。

后续所有示例中的 `uv run --with Pillow python`（包括带 `--with pillow-heif` 的形式）均可替换为已验证的 `"<PYTHON>"`；PowerShell 使用 `& "<PYTHON>"`。其余子命令和参数不变，依赖安装与运行必须使用同一个解释器。

## 文生图

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py generate \
  --prompt '竖版3:4旅行海报，森林晨雾，顶部标题“去山里”，底部小字“慢一点，看见更多”。字体清楚，低饱和绿色。' \
  --size 1536x2048 --output-format png --out /absolute/output/travel
```

## 多图参考、交互编辑

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py edit \
  --image /absolute/input/subject.png --image /absolute/input/scene.jpg \
  --prompt '将图1<bbox>179 283 796 986</bbox>的主体放到图2<bbox>118 331 933 871</bbox>位置，保持主体外观，让光线与场景一致。' \
  --size 2K --optimize standard --out /absolute/output/composite
```

## 保留透明背景的编辑

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py edit \
  --image /absolute/input/alpha-logo.png --prompt '把金色图案改成银色，保持文字、轮廓与透明背景。' \
  --background transparent --out /absolute/output/silver-logo
```

## 图层拆分

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py layers \
  --image /absolute/input/poster.png --size auto \
  --prompt '将主标题、人物与前景装饰分别拆为图层。' \
  --output-format jpeg --out /absolute/output/poster-layers
```

省略prompt可自动拆图。输出JPEG底图、透明PNG图层及包含坐标、层级的元数据。

## 完整官方JSON与预览

保存为自己的request.json：

```json
{
  "model": "doubao-seedream-5-0-pro-260628",
  "prompt": "把图1杯子改为蓝色，保持轮廓和背景不变",
  "image": "https://example.com/your-public-image.png",
  "layer_decomposition": false,
  "size": "1.5K",
  "optimize_prompt_options": {"mode": "fast"},
  "background": "opaque",
  "output_format": "png",
  "response_format": "b64_json",
  "watermark": false
}
```

替换示例URL后执行。JSON中的image仅接受URL/Data URI，本地路径使用--image。

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py edit \
  --request /absolute/request.json --dry-run
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py edit \
  --request /absolute/request.json --out /absolute/output/edit-final
```

## 仅恢复下载

```bash
uv run --with Pillow python <SKILL_DIR>/scripts/seedream.py download \
  --response /absolute/output/poster-layers/response.json \
  --out /absolute/output/poster-layers-recovered
```

无需密钥，不发生成请求；在新目录重新保存响应中的全部图片。URL过期时无法靠重试下载恢复，不自动重新付费生成。

## 本地HEIC/HEIF与测试

```bash
uv run --with Pillow --with pillow-heif python <SKILL_DIR>/scripts/seedream.py edit \
  --image /absolute/input/photo.heic --prompt '保持主体，只改成柔和暖色灯光' \
  --out /absolute/output/warm-light
uv run --with Pillow --with pillow-heif python -m unittest discover \
  -s <SKILL_DIR>/scripts -p 'test_*.py' -v
```

测试只访问本地临时HTTP服务，使用随机测试凭据，不调用方舟。
