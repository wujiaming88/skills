---
name: ppt-from-template
description: "Create PPT presentations from existing .pptx templates using a two-phase workflow: Phase 1 plans content into plan.yaml, Phase 2 delegates XML editing to a sub-agent. Use when: (1) user asks to make a PPT/课件/演示文稿/幻灯片 from a template, (2) user has a .pptx template and wants new content filled in, (3) user says '做个PPT', '用模板做', '基于模板生成'. Requires pptx skill scripts. NOT for: creating PPT from scratch without a template (use pptx skill instead)."
---

# PPT from Template

Two-phase workflow: **plan** content (Phase 1, main session) → **build** PPT (Phase 2, sub-agent).

## Directory Conventions

| Path | Purpose |
|------|---------|
| `{workspace}/template/` | Source .pptx templates (never modified) |
| `{workspace}/output/` | Final output files |
| `{workspace}/plan.yaml` | Content plan (intermediate artifact) |
| `/tmp/ppt-work/` | Temporary unpack/edit directory |
| `~/.openclaw/skills/pptx/scripts/` | pptx skill scripts (unpack, pack, clean, thumbnail) |

`{workspace}` = the current agent's workspace directory.

## Phase 1: Plan (main session)

Goal: produce `plan.yaml`. **Do not touch XML.**

### 1. Analyze template layouts

```bash
# Extract text to identify placeholder content
python3 -m markitdown "{workspace}/template/TEMPLATE.pptx"

# Generate thumbnails if soffice available
python3 ~/.openclaw/skills/pptx/scripts/thumbnail.py "{workspace}/template/TEMPLATE.pptx"
```

Show layout options to user. Identify each slide's number and role (cover, toc, content, stats, section, ending, etc.).

### 2. Discuss content with user

Confirm: page count, layout per page, text/data/images per page.

### 3. Generate plan.yaml

Write `{workspace}/plan.yaml`. See [references/plan-schema.md](references/plan-schema.md) for schema and examples.

Key rules:
- `source` references a slide filename from the template (e.g. `slide3.xml`)
- Same source can be reused across multiple entries
- `content` is free-form per role — titles, body text, stats, items, etc.
- User confirms plan before Phase 2

## Phase 2: Build (sub-agent)

Spawn a sub-agent with the prompt template from [references/build-prompt.md](references/build-prompt.md).

```python
sessions_spawn({
    task: "<prompt from build-prompt.md, with paths filled in>",
    agentId: "waicode",
    label: "PPT-MAKE",
    runTimeoutSeconds: 600
})
```

The sub-agent will: unpack → trim unused slides → edit content per plan → clean orphans → pack → compress → output.

## Iteration

To modify output, edit `plan.yaml` and re-run Phase 2. No need to redo Phase 1.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Template too large | Phase 2 trims to only referenced slides first |
| XML too large to read | `grep` to locate text, then `edit` tool for surgical replacement |
| Many pages | Parallelize sub-agents (2-3 slides each) |
| Output file too large | Use `scripts/compress_pptx.py` for ZIP + image optimization |
| Pack fails validation | Ensure `--original` flag references the source template |
