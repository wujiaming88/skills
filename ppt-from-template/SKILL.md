---
name: ppt-from-template
description: "Create PPT presentations from existing .pptx templates using a two-phase workflow: Phase 1 plans content into plan.yaml, Phase 2 delegates XML editing to sub-agents. Supports 5-50+ slides via parallel batch editing. Use when: (1) user asks to make a PPT/课件/演示文稿/幻灯片 from a template, (2) user has a .pptx template and wants new content filled in, (3) user says '做个PPT', '用模板做', '基于模板生成'. Requires pptx skill scripts. NOT for: creating PPT from scratch without a template (use pptx skill instead)."
---

# PPT from Template

Two-phase workflow: **plan** content (Phase 1, main session) → **build** PPT (Phase 2, sub-agents).

## Directory Conventions

| Path | Purpose |
|------|---------|
| `{workspace}/template/` | Source .pptx templates (never modified) |
| `{workspace}/output/` | Final output files |
| `{workspace}/plan.yaml` | Content plan (intermediate artifact) |
| `/tmp/ppt-work/` | Temporary unpack/edit directory (shared across agents) |
| `~/.openclaw/skills/pptx/scripts/` | pptx skill scripts (unpack, pack, clean, thumbnail) |

`{workspace}` = the current agent's workspace directory.

## Phase 1: Plan (main session)

Goal: produce `plan.yaml`. **Do not touch XML.**

### 1. Analyze template layouts

```bash
python3 -m markitdown "{workspace}/template/TEMPLATE.pptx"
python3 ~/.openclaw/skills/pptx/scripts/thumbnail.py "{workspace}/template/TEMPLATE.pptx"
```

Show layout options to user. Identify each slide's number and role.

### 2. Discuss content with user

Confirm: page count, layout per page, text/data/images per page.

### 3. Generate plan.yaml

Write `{workspace}/plan.yaml`. See [references/plan-schema.md](references/plan-schema.md) for schema and examples.

## Phase 2: Build (sub-agents)

Phase 2 uses a **3-step pipeline** to avoid timeout on large decks. See [references/build-prompt.md](references/build-prompt.md) for prompt templates.

### Scaling strategy

| Slide count | Strategy | Estimated time |
|-------------|----------|----------------|
| ≤15 | Single agent (all-in-one) | 5-8 min |
| 16-30 | Prep → 2 edit agents (parallel) → Pack | 6-10 min |
| 31-50+ | Prep → 3-4 edit agents (parallel) → Pack | 8-12 min |

### Step 1: Prep agent

Unpack template, trim to only referenced slides, clean orphans. Fast (~2 min).

```python
sessions_spawn({
    task: "<prep prompt from build-prompt.md>",
    agentId: "waicode",
    label: "PPT-PREP",
    runTimeoutSeconds: 300
})
```

**Wait for completion before Step 2.** The unpacked directory must be ready.

### Step 2: Edit agents (parallel)

Split plan.yaml slides into batches of 5-8. Spawn one agent per batch **in parallel**.

```python
# Batch 1: slides 1-8
sessions_spawn({
    task: "<edit prompt for slides 1-8>",
    agentId: "waicode",
    label: "PPT-EDIT-1",
    runTimeoutSeconds: 480
})
# Batch 2: slides 9-16
sessions_spawn({
    task: "<edit prompt for slides 9-16>",
    agentId: "waicode",
    label: "PPT-EDIT-2",
    runTimeoutSeconds: 480
})
# ... more batches as needed
```

Each agent edits its assigned slides in `/tmp/ppt-work/unpacked/`. No conflicts because each agent works on different slide files.

**Wait for ALL edit agents to complete before Step 3.**

### Step 3: Pack agent

Pack, compress, output. Fast (~2 min).

```python
sessions_spawn({
    task: "<pack prompt from build-prompt.md>",
    agentId: "waicode",
    label: "PPT-PACK",
    runTimeoutSeconds: 300
})
```

### Small decks shortcut (≤15 slides)

For ≤15 slides, use a single all-in-one agent instead of the 3-step pipeline:

```python
sessions_spawn({
    task: "<all-in-one prompt from build-prompt.md>",
    agentId: "waicode",
    label: "PPT-MAKE",
    runTimeoutSeconds: 600
})
```

## Iteration

Edit `plan.yaml` and re-run Phase 2. No need to redo Phase 1.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Timeout on large deck | Use 3-step pipeline with parallel edit agents |
| Template too large | Prep step trims to only referenced slides |
| XML too large to read | `grep` to locate text, then `edit` for surgical replacement |
| Output file too large | `scripts/compress_pptx.py` for ZIP + image optimization |
| Edit conflict | Each batch edits different slide files — no conflicts |
| One batch fails | Re-run only that batch, others already done on disk |
