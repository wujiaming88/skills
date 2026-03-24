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

| Slide count | Strategy | Edit agents | Estimated time |
|-------------|----------|-------------|----------------|
| ≤15 | Single agent (all-in-one) | 1 | 3-5 min |
| 16-25 | Prep → 4 edit agents → Pack | 4 | 4-6 min |
| 26-40 | Prep → 5-6 edit agents → Pack | 5-6 | 5-8 min |
| 41-50+ | Prep → 6-8 edit agents → Pack | 6-8 | 6-10 min |

**Target 4-5 slides per batch.** More, smaller batches finish faster than fewer, larger ones.

### Step 1: Prep agent

Unpack template, trim to only referenced slides, clean orphans, **run fix_rels.py**, **generate edits.json**. Fast (~2-3 min).

```python
sessions_spawn({
    task: "<prep prompt from build-prompt.md>",
    agentId: "waicode",
    label: "PPT-PREP",
    runTimeoutSeconds: 300
})
```

Prep agent must:
1. Unpack + trim + clean
2. `python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked`
3. `python3 {skill_dir}/scripts/gen_edits.py /tmp/ppt-work/unpacked {workspace}/plan.yaml /tmp/ppt-work/edits.json`

**Wait for completion before Step 2.** Both unpacked directory and edits.json must be ready.

### Step 2: Edit agents (parallel)

Split slides into batches of **4-5**. Each agent runs `apply_edits.py` with its assigned slides — **no grep/read/edit needed**.

```python
# Batch 1: slides 1-5
sessions_spawn({
    task: "python3 {skill_dir}/scripts/apply_edits.py /tmp/ppt-work/unpacked /tmp/ppt-work/edits.json slide1.xml slide2.xml slide3.xml slide4.xml slide5.xml",
    agentId: "waicode",
    label: "PPT-EDIT-1",
    runTimeoutSeconds: 120
})
# Batch 2: slides 6-10
sessions_spawn({
    task: "python3 {skill_dir}/scripts/apply_edits.py /tmp/ppt-work/unpacked /tmp/ppt-work/edits.json slide6.xml slide7.xml slide8.xml slide9.xml slide10.xml",
    agentId: "waicode",
    label: "PPT-EDIT-2",
    runTimeoutSeconds: 120
})
# ... more batches
```

If apply_edits reports missed replacements, spawn a **fix agent** for manual grep→edit on those slides only.

**Wait for ALL edit agents to complete before Step 3.**

### Step 3: Pack agent

**Run fix_rels.py** (second pass to catch edit-phase orphans), then pack, compress, output. Fast (~2 min).

```python
sessions_spawn({
    task: "<pack prompt from build-prompt.md>",
    agentId: "waicode",
    label: "PPT-PACK",
    runTimeoutSeconds: 300
})
```

Pack agent must run `fix_rels.py` before packing:
```bash
python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked
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
| Timeout on large deck | 4-5 slides/batch, apply_edits.py (~30s/batch vs 8min grep/edit) |
| apply_edits misses text | Spawn fix agent: grep + manual edit for those slides only |
| Template too large | Prep step trims to only referenced slides |
| XML too large to read | apply_edits.py handles XML directly — no manual read needed |
| Output file too large | `scripts/compress_pptx.py` for ZIP + image optimization |
| Broken rels after trim | Prep runs `fix_rels.py` after trimming |
| Broken rels after edit | Pack runs `fix_rels.py` before packing |
| Edit conflict | Each batch targets different slide files — no conflicts |
| One batch fails | Re-run only that batch, others already done on disk |
