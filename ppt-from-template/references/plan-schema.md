# plan.yaml Schema

## Top-level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `template` | string | yes | Absolute path to source .pptx template |
| `output` | string | yes | Absolute path for output .pptx file |
| `slides` | list | yes | Ordered list of slide entries |

## Slide Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Template slide filename (e.g. `slide3.xml`) |
| `role` | string | yes | Semantic label: cover, toc, content, stats, section, ending, etc. |
| `content` | object | yes | Free-form content to fill in — structure varies by role |

## Example

```yaml
template: /path/to/template.pptx
output: /path/to/output.pptx

slides:
  - source: slide1.xml
    role: cover
    content:
      title: "2026 年度战略报告"
      subtitle: "市场拓展与技术升级"
      date: "2026年3月"

  - source: slide7.xml
    role: toc
    content:
      items:
        - "一、市场现状分析"
        - "二、竞争格局"
        - "三、战略规划"

  - source: slide12.xml
    role: content
    content:
      title: "市场现状分析"
      body: |
        2025 年行业规模达 520 亿，
        同比增长 18%。

  - source: slide5.xml
    role: stats
    content:
      title: "关键指标"
      stats:
        - label: "营收增长"
          value: "+42%"
        - label: "客户数"
          value: "1,200+"

  - source: slide5.xml      # same layout reused
    role: stats
    content:
      title: "技术投入"
      stats:
        - label: "研发占比"
          value: "18%"

  - source: slide20.xml
    role: ending
    content:
      title: "谢谢"
      contact: "team@company.com"
```

## Notes

- Same `source` can appear in multiple entries (slide will be duplicated).
- `content` structure is flexible — adapt keys to match the template's placeholders.
- The sub-agent uses `content` values to locate and replace text in slide XML.
