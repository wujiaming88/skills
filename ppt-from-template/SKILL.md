---
name: ppt-from-template
description: >
  Generate complete PowerPoint presentations from a .pptx template file and a user-provided topic.
  Three-step workflow: analyze template layouts, draft content outline, assemble output.
  All text replacement via python-pptx API only — never edit XML directly.
  Triggers: PPT、模板、演示文稿、幻灯片、课件、做个PPT、slide deck、presentation、
  根据模板生成、用模板做、帮我做个PPT、template-based slides.
  NOT for: creating PPT from scratch without a template, PDF/Word conversion.
---

# PPT From Template

Three-step generation: analyze template → draft plan → assemble output.

## Prerequisites

- Python 3.7+, python-pptx, PyYAML
- User-provided `.pptx` template file

## Workflow

### Step 1: Analyze Template (one-time)

```bash
python3 scripts/analyze_template.py <template.pptx> <work_dir>
```

Read the output `layouts.yaml`. Present available layouts to the user for confirmation.

### Step 2: Draft plan.yaml

Compose an outline based on user topic + available layouts. Rules:

- Page 1: `cover` layout
- Chapter openers: `section` layout
- Body pages: `content` or `image-text`
- Last page: `cover` or `section` as ending
- Body list: 3–6 items, each ≤ 25 chars; title ≤ 15 chars

Format spec: [references/plan-schema.md](references/plan-schema.md)

Present the outline to the user. Proceed to Step 3 only after confirmation.

### Step 3: Assemble

```bash
python3 scripts/assemble_ppt.py <template.pptx> <plan.yaml> <output.pptx>
```

Send the generated `.pptx` to the user.

## Constraints

### Compatibility (highest priority)

- **Never edit XML directly.** Use python-pptx `text_frame` API for all text operations.
- Slide copying via `deep_copy_slide()` preserves formats, media, and relationships.

### Iteration

Modify `plan.yaml`, re-run `assemble_ppt.py`. No need to re-analyze the template.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| PPT won't open | Direct XML edit | Use python-pptx API only |
| Text not replaced | Shape role mismatch | Check `layouts.yaml` placeholders |
| Missing images | Incomplete slide copy | `deep_copy_slide` handles this |
| Wrong page count | Bad `source_slide` | Verify against template slide numbers |
