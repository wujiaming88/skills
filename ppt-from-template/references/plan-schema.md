# plan.yaml Schema

```yaml
title: "演示文稿标题"

slides:
  - layout: cover          # cover | section | content | image-text | data | other
    source_slide: 1         # template slide number (1-based, from layouts.yaml)
    content:
      title: "标题"         # ≤15 chars
      subtitle: "副标题"    # ≤30 chars, optional

  - layout: section
    source_slide: 10
    content:
      title: "第一章"

  - layout: content
    source_slide: 11
    content:
      title: "要点页"
      body:                 # list → one paragraph per item; string → single paragraph
        - "要点一"          # each ≤25 chars, max 6 items
        - "要点二"

  - layout: content
    source_slide: 11
    content:
      title: "段落页"
      body: "一整段文字说明。"
```

## Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | ✅ | Presentation title |
| `slides` | array | ✅ | Slide list |
| `slides[].layout` | string | ✅ | Layout type from `layouts.yaml` |
| `slides[].source_slide` | int | ✅ | Template slide number (1-based) |
| `slides[].content.title` | string | optional | |
| `slides[].content.subtitle` | string | optional | |
| `slides[].content.body` | string or array | optional | Array = bullet list; string = paragraph |

## Notes

- Same `source_slide` can be reused across multiple slides.
- Images and charts retain template originals; only text is replaced.
- Empty `body: []` clears the text area but preserves the shape.
