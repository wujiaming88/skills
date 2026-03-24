# Build Prompt Templates

Four prompt templates for Phase 2. Replace `{placeholders}` with actual values.

---

## 1. All-in-One Prompt (≤15 slides)

Use for small decks. Single agent does everything.

```
Create a PPT from plan.yaml.

plan.yaml: {workspace}/plan.yaml
pptx scripts: ~/.openclaw/skills/pptx/scripts/
skill scripts: {skill_dir}/scripts/
editing rules: ~/.openclaw/skills/pptx/editing.md

Steps:
1. Read plan.yaml
2. Unpack: rm -rf /tmp/ppt-work/ && mkdir -p /tmp/ppt-work/ && python3 ~/.openclaw/skills/pptx/scripts/office/unpack.py "{template_path}" /tmp/ppt-work/unpacked/
3. Trim: in presentation.xml, keep only <p:sldId> for plan's source slides. Remove others.
4. Duplicate slides if same source used multiple times. Update presentation.xml and _rels/.
5. Reorder slides to match plan sequence.
6. Clean: python3 ~/.openclaw/skills/pptx/scripts/clean.py /tmp/ppt-work/unpacked/
7. Fix rels: python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked/
8. Gen edits: python3 {skill_dir}/scripts/gen_edits.py /tmp/ppt-work/unpacked/ {workspace}/plan.yaml /tmp/ppt-work/edits.json
9. Apply edits: python3 {skill_dir}/scripts/apply_edits.py /tmp/ppt-work/unpacked /tmp/ppt-work/edits.json
10. If any missed: manual grep → edit for those slides only.
11. Fix rels (second pass): python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked/
12. Pack: python3 ~/.openclaw/skills/pptx/scripts/office/pack.py /tmp/ppt-work/unpacked/ /tmp/ppt-work/output.pptx --original "{template_path}"
13. Compress: python3 {skill_dir}/scripts/compress_pptx.py /tmp/ppt-work/output.pptx /tmp/ppt-work/final.pptx
14. Output: mkdir -p {workspace}/output/ && cp /tmp/ppt-work/final.pptx "{output_path}"
15. Cleanup: rm -rf /tmp/ppt-work/
```

---

## 2. Prep Prompt (pipeline Step 1)

Unpack, trim, fix rels, generate edits.json. Do NOT edit slide content.

```
Prepare the template for editing.

pptx scripts: ~/.openclaw/skills/pptx/scripts/
skill scripts: {skill_dir}/scripts/
plan.yaml: {workspace}/plan.yaml

Steps:
1. rm -rf /tmp/ppt-work/ && mkdir -p /tmp/ppt-work/
2. python3 ~/.openclaw/skills/pptx/scripts/office/unpack.py "{template_path}" /tmp/ppt-work/unpacked/
3. In presentation.xml, keep only these <p:sldId> entries: {source_slide_list}. Remove all others.
4. If any source is used multiple times: {duplicate_instructions}
5. Reorder slides to final sequence: {slide_order}
6. python3 ~/.openclaw/skills/pptx/scripts/clean.py /tmp/ppt-work/unpacked/
7. python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked/
8. python3 {skill_dir}/scripts/gen_edits.py /tmp/ppt-work/unpacked/ {workspace}/plan.yaml /tmp/ppt-work/edits.json
9. Verify: ls /tmp/ppt-work/unpacked/ppt/slides/ should show exactly {total_slides} slides.
10. Verify: cat /tmp/ppt-work/edits.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} slides, {sum(len(v) for v in d.values())} edits')"

Do NOT edit any slide content. Do NOT pack. Leave /tmp/ppt-work/unpacked/ and edits.json ready.
```

---

## 3. Edit Prompt (pipeline Step 2, one per batch)

**Fast mode**: apply pre-generated edits. No grep/read/edit needed.

```
Apply edits to assigned slides.

skill scripts: {skill_dir}/scripts/

Run:
  python3 {skill_dir}/scripts/apply_edits.py /tmp/ppt-work/unpacked /tmp/ppt-work/edits.json {slide_list}

Check the output. If any replacements failed (❌ lines):
  1. grep for similar text in those slide XMLs
  2. Use edit tool for manual fix

Do NOT touch slides outside your batch.
Do NOT unpack, clean, or pack.
```

---

## 4. Pack Prompt (pipeline Step 3)

Pack the edited directory into final output.

```
Pack the edited PPT directory into a final file.

pptx scripts: ~/.openclaw/skills/pptx/scripts/
fix_rels script: {skill_dir}/scripts/fix_rels.py
compress script: {workspace}/skills/ppt-from-template/scripts/compress_pptx.py

Steps:
1. Verify slides exist: ls /tmp/ppt-work/unpacked/ppt/slides/
2. Fix rels (second pass): python3 {skill_dir}/scripts/fix_rels.py /tmp/ppt-work/unpacked/
3. Pack: python3 ~/.openclaw/skills/pptx/scripts/office/pack.py /tmp/ppt-work/unpacked/ /tmp/ppt-work/output.pptx --original "{template_path}"
4. Compress: python3 {compress_script} /tmp/ppt-work/output.pptx /tmp/ppt-work/final.pptx
5. Output: mkdir -p {workspace}/output/ && cp /tmp/ppt-work/final.pptx "{output_path}"
6. Report file size and slide count.
7. Cleanup: rm -rf /tmp/ppt-work/
```

---

## Batch Splitting Guide

When splitting slides into batches:
- **Target 4-5 slides per batch** (smaller batches, more parallelism, lower timeout risk)
- Each batch runs apply_edits.py with its slide filenames — very fast (~30s per batch)
- Fallback: if apply_edits misses replacements, spawn a fix agent for those slides only
- Example: 30 slides → 6 batches of 5 → 6 agents parallel → done in ~1-2 min
