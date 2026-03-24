# plan.yaml 格式说明

## 完整示例

```yaml
title: "OpenClaw 产品介绍"

slides:
  # 封面
  - layout: cover
    source_slide: 1
    content:
      title: "OpenClaw 产品介绍"
      subtitle: "新一代 AI Agent 平台"

  # 章节页
  - layout: section
    source_slide: 8
    content:
      title: "第一章 产品概述"

  # 内容页（列表）
  - layout: content
    source_slide: 11
    content:
      title: "核心功能"
      body:
        - "多 Agent 协作框架"
        - "200+ 内置技能"
        - "全平台消息集成"
        - "企业级安全架构"

  # 内容页（纯文本）
  - layout: content
    source_slide: 11
    content:
      title: "技术架构"
      body: "基于 Gateway 的分布式架构，支持本地和云端混合部署，通过 WebSocket 实现实时通信。"

  # 结尾
  - layout: cover
    source_slide: 1
    content:
      title: "谢谢"
      subtitle: "联系我们: hello@openclaw.ai"
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 演示文稿标题 |
| `slides` | array | ✅ | 页面列表 |
| `slides[].layout` | string | ✅ | 版式类型：cover/section/content/image-text/data/other |
| `slides[].source_slide` | int | ✅ | 模板中的源 slide 编号（1-based，从 layouts.yaml 获取） |
| `slides[].content` | object | ✅ | 该页内容 |
| `content.title` | string | 可选 | 标题文字（≤15 字） |
| `content.subtitle` | string | 可选 | 副标题（≤30 字） |
| `content.body` | string/array | 可选 | 正文。字符串=段落，数组=要点列表（每条 ≤25 字，≤6 条） |

## 版式类型

| 类型 | 说明 | 典型占位符 |
|------|------|-----------|
| `cover` | 封面/结尾 | title + subtitle |
| `section` | 章节分隔页 | title |
| `content` | 内容页 | title + body（列表或段落） |
| `image-text` | 图文混排 | title + body + 图片（图片保留原始） |
| `data` | 数据展示 | title + 表格/图表（保留原始） |
| `other` | 其他 | 按实际占位符匹配 |

## 注意事项

- `source_slide` 必须引用 `layouts.yaml` 中存在的 slide 编号
- 同一 `source_slide` 可以被多次引用（多页使用同一版式）
- 图片和表格保留模板原始内容，只替换文本
- body 为数组时，每个元素独立成段；为字符串时合为一段
