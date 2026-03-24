---
name: ppt-from-template
description: >
  根据 PPT 模板和用户主题，生成完整演示文稿。先分析模板版式，再构思内容大纲，最后组装生成。
  全程使用 python-pptx API，确保文件兼容性（PowerPoint/WPS/Keynote 零警告打开）。
  触发词：PPT、模板、演示文稿、幻灯片、课件、做个PPT、slide deck、presentation、
  根据模板生成、用模板做。
  不适用：从零创建无模板 PPT、纯 PDF/Word 转换。
---

# PPT From Template

根据模板版式 + 用户主题，三步生成 PPT。

## 前置条件

- Python 3.7+, python-pptx, PyYAML (`pip install python-pptx pyyaml`)
- 用户提供 `.pptx` 模板文件

## 核心流程

### Step 1: 分析模板（一次性）

执行 `scripts/analyze_template.py` 解析模板：

```bash
python3 scripts/analyze_template.py <template.pptx> <work_dir>
```

输出 `layouts.yaml`，包含：
- 每种版式类型（cover/section/content/image-text/data/other）
- 每种版式的代表 slide 编号
- 可编辑占位符（位置、角色、字号）

读取 `layouts.yaml`，向用户**展示可用版式**并确认。

### Step 2: 构思内容，生成 plan.yaml

根据用户主题 + 可用版式，构思大纲。规则：
- 第 1 页固定用 `cover` 版式
- 每章开头用 `section` 版式
- 正文用 `content` / `image-text` 版式
- 最后一页用 `cover` 或 `section` 做结尾
- 每页 body 列表控制在 3-6 条，避免溢出

输出 `plan.yaml`，格式参见 [references/plan-schema.md](references/plan-schema.md)。

**向用户展示大纲**，确认后再执行 Step 3。

### Step 3: 组装生成

执行 `scripts/assemble_ppt.py`：

```bash
python3 scripts/assemble_ppt.py <template.pptx> <plan.yaml> <output.pptx>
```

脚本自动完成：复制版式页 → 删除原始页 → 替换文本 → 保存。

### 输出给用户

将生成的 `.pptx` 文件发送给用户。

## 关键约束

### 兼容性（最高优先级）
- **禁止直接操作 XML**。所有文本替换通过 python-pptx 的 text_frame API
- 复制 slide 使用 `deep_copy_slide()` 函数，保留原始格式和媒体关系
- 不删除模板中的任何媒体/关系文件，只通过复制目标页避免引用断裂

### 防超时
- 页数 ≤ 20：单次执行 assemble_ppt.py（通常 < 1 分钟）
- 页数 > 20：仍然单次执行（脚本本身很快，瓶颈在 AI 构思内容而非脚本执行）
- 如果 plan.yaml 内容量大，分批写入 plan.yaml（先写前 15 页，再 append 后续页）

### 内容质量
- 每页 body 最多 6 条要点
- 每条要点不超过 25 个字
- 标题不超过 15 个字
- 副标题不超过 30 个字

## 迭代修改

用户反馈后：
1. 修改 `plan.yaml` 中对应页的 content
2. 重新执行 `assemble_ppt.py` 即可
3. 无需重新分析模板

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| PPT 打开报错 | 直接操作了 XML | 必须用 python-pptx API |
| 文字没替换 | 形状角色匹配失败 | 检查 layouts.yaml 中的占位符 |
| 格式丢失 | 未保留原 run 格式 | assemble_ppt.py 已处理 |
| 图片丢失 | slide 复制不完整 | deep_copy_slide 已复制关系 |
| 页数不对 | plan.yaml source_slide 错误 | 检查编号是否对应模板 |
