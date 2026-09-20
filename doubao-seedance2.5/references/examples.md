# 请求示例

示例中的 `https://media.example.com/...` 和 `asset://...` 是需替换的素材位置，不是可用测试素材。先保存 JSON，再执行 `create --request request.json --dry-run`；确认用户要生成后去掉 `--dry-run`。所有请求固定同一模型，JSON 省略 model 时 CLI 自动补入。

## 多模态生成选项

此示例展示可组合的多模态字段，不表示每次都应开启回调或尾帧；按用户用途取舍。联网搜索仅支持纯文本，使用下方单独示例。

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "生成一个新产品短片：参考 @图片1 的杯身花纹、@视频1 的环绕运镜和 @音频1 的音乐节奏。清晨木桌上茶杯冒着热气，无对白。"},
    {"type": "image_url", "image_url": {"url": "https://media.example.com/cup.png"}, "role": "reference_image"},
    {"type": "video_url", "video_url": {"url": "https://media.example.com/camera.mov"}, "role": "reference_video"},
    {"type": "audio_url", "audio_url": {"url": "https://media.example.com/music.wav"}, "role": "reference_audio"}
  ],
  "omni_reference_task_type": "reference",
  "resolution": "720p",
  "ratio": "16:9",
  "duration": 5,
  "generate_audio": true,
  "watermark": false,
  "output_format": "mp4",
  "return_last_frame": true,
  "callback_url": "https://callback.example.com/seedance",
  "execution_expires_after": 3600,
  "priority": 0,
  "safety_identifier": "anonymous-user-hash",
  "service_tier": "default"
}
```

```bash
python3 {baseDir}/scripts/seedance.py create --request request.json \
  --wait --receipt output/seedance/task.json \
  --out output/seedance/video.mp4 --last-frame-out output/seedance/last.jpg
```

## 纯文本联网搜索

```bash
python3 {baseDir}/scripts/seedance.py create \
  --prompt "微距镜头对准叶片上翠绿的玻璃蛙，焦点从皮肤转移到透明腹部的心脏" \
  --web-search --resolution 720p --ratio 16:9 --duration 5 \
  --wait --out output/seedance/glass-frog.mp4
```

检查返回的 `usage.tool_usage.web_search`；值为 0 表示模型没有执行搜索。不要额外添加参考素材。

## 首帧与首尾帧

```bash
python3 {baseDir}/scripts/seedance.py create \
  --first-frame start.png --last-frame end.png \
  --prompt "镜头平稳向前，场景由清晨过渡到黄昏，自然衔接起止画面" \
  --ratio adaptive --duration 5 --no-generate-audio \
  --wait --out output/seedance/transition.mp4
```

只要首帧时去掉 `--last-frame`；无提示词的图生视频也受支持。不要再追加任何 `--reference-*` 素材。

## 纯音频参考

```bash
python3 {baseDir}/scripts/seedance.py create \
  --reference-audio rhythm.wav \
  --prompt "根据 @音频1 的节奏生成全新抽象动态图形，色块随鼓点变化" \
  --omni-reference-task-type reference --ratio 9:16 --duration 8 \
  --wait --out output/seedance/rhythm.mp4
```

`--reference-image/--reference-audio` 可接受本地路径、Data URI、公网 URL、`asset://ID`；`--reference-video` 仅接受 URL 或 asset ID。多个素材重复传对应开关。

## 视频编辑

```json
{
  "content": [
    {"type": "text", "text": "编辑 @视频1：把桌面的杯子替换为 @图片1 的茶杯，保留手部动作、背景、运镜和原声音。"},
    {"type": "video_url", "video_url": {"url": "https://media.example.com/source.mov"}, "role": "reference_video"},
    {"type": "image_url", "image_url": {"url": "asset://user-approved-cup"}, "role": "reference_image"}
  ],
  "omni_reference_task_type": "edit",
  "ratio": "adaptive",
  "duration": -1,
  "resolution": "720p",
  "output_format": "mov",
  "generate_audio": true
}
```

执行时输出文件使用 `.mov`。需要编辑音轨时，明确保留/替换人声、音乐、音效；不要用无声输出代替“去掉背景音乐”。

## 视频延长

```bash
python3 {baseDir}/scripts/seedance.py create \
  --reference-video 'https://media.example.com/source.mov' \
  --prompt "向后延长 @视频1，衔接末尾镜头与音乐，人物继续向前走进花园" \
  --omni-reference-task-type extend --ratio adaptive --duration 5 \
  --output-format mov --wait --out output/seedance/continuation.mov
```

向前延长时修改提示词方向。不得仅因返回文件就宣称它包含原片与新增片段的完整合并；检查实际内容。

## 分页与筛选

```bash
python3 {baseDir}/scripts/seedance.py list \
  --page-num 1 --page-size 100 --status succeeded \
  --task-id TASK_A --task-id TASK_B

python3 {baseDir}/scripts/seedance.py list --endpoint-id ep-EXAMPLE --service-tier default
```

重复 ID 编码为 `filter.task_ids=TASK_A&filter.task_ids=TASK_B`。翻页直到已读取 total 或 items 为空；每页最多 500 项，列表频率不超过账号上限。不要将 Model ID 传给 `--endpoint-id`。

## 超时恢复与单独下载尾帧

```bash
python3 {baseDir}/scripts/seedance.py wait TASK_ID --wait-timeout 600
python3 {baseDir}/scripts/seedance.py download TASK_ID \
  --out output/seedance/recovered.mp4 --last-frame-out output/seedance/recovered.jpg
```

只下载尾帧时省略 `--out`；必须在原始创建时已设置 `return_last_frame=true`。2026-09-18 实测尾帧是 JPEG，因此示例使用 `.jpg`；若服务返回 PNG，按 CLI 的格式提示换成 `.png`。不要仅凭 URL 后缀判断格式。任务已失败时先 `get TASK_ID` 读取 error，修正后才决定是否创建新的付费任务。
