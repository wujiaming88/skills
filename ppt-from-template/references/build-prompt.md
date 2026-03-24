# Build Prompt Templates

Four prompt templates for Phase 2. Replace `{placeholders}` with actual values.

---

## 1. All-in-One Prompt (≤15 slides)

Use for small decks. Single agent does everything.

```
Create a PPT from plan.yaml.

plan.yaml: {workspace}/plan.yaml
pptx scripts: ~/.openclaw/skills/pptx/scripts/
editing rules: ~/.openclaw/skills/pptx/editing.md

Steps:
1. Read plan.yaml
2. Unpack: rm -rf /tmp/ppt-work/ && mkdir -p /tmp/ppt-work/ && python3 ~/.openclaw/skills/pptx/scripts/office/unpack.py "{template_path}" /tmp/ppt-work/unpacked/
3. Trim: in presentation.xml, keep only <p:sldId> for plan's source slides. Remove others.
4. Duplicate slides if same source used multiple times. Update presentation.xml and _rels/.
5. Reorder slides to match plan sequence.
6. Clean: python3 ~/.openclaw/skills/pptx/scripts/clean.py /tmp/ppt-work/unpacked/
7. Edit each slide: grep to locate text → edit tool to replace. Preserve <a:pPr>.
8. Pack: python3 ~/.openclaw/skills/pptx/scripts/office/pack.py /tmp/ppt-work/unpacked/ /tmp/ppt-work/output.pptx --original "{template_path}"
9. Compress: python3 {workspace}/skills/ppt-from-template/scripts/compress_pptx.py /tmp/ppt-work/output.pptx /tmp/ppt-work/final.pptx
10. Output: mkdir -p {workspace}/output/ && cp /tmp/ppt-work/final.pptx "{output_path}"
11. Cleanup: rm -rf /tmp/ppt-work/

Slide edits:
{slide_edit_instructions}

Rules: edit tool only (no sed), grep first, preserve <a:pPr>, multi-items use multiple <a:p>.
```

---

## 2. Prep Prompt (pipeline Step 1)

Unpack and trim only. Do NOT edit slide content.

```
Prepare the template for editing.

pptx scripts: ~/.openclaw/skills/pptx/scripts/

Steps:
1. rm -rf /tmp/ppt-work/ && mkdir -p /tmp/ppt-work/
2. python3 ~/.openclaw/skills/pptx/scripts/office/unpack.py "{template_path}" /tmp/ppt-work/unpacked/
3. In presentation.xml, keep only these <p:sldId> entries: {source_slide_list}. Remove all others.
4. If any source is used multiple times: {duplicate_instructions}
5. Reorder slides to final sequence: {slide_order}
6. python3 ~/.openclaw/skills/pptx/scripts/clean.py /tmp/ppt-work/unpacked/
7. Verify: ls /tmp/ppt-work/unpacked/ppt/slides/ should show exactly {total_slides} slides.

Do NOT edit any slide content. Do NOT pack. Leave /tmp/ppt-work/unpacked/ ready for editing.
```

---

## 3. Edit Prompt (pipeline Step 2, one per batch)

Edit a specific batch of slides. Runs in parallel with other batches.

```
Edit slides in an already-unpacked PPT directory.

Directory: /tmp/ppt-work/unpacked/
editing rules: ~/.openclaw/skills/pptx/editing.md

You are responsible for editing ONLY these slides:
{batch_slide_edits}

For each slide:
1. grep to locate the placeholder text in the slide XML
2. Use edit tool for precise replacement
3. Preserve all <a:pPr> formatting
4. For multi-item content, use separate <a:p> elements

Do NOT touch slides outside your batch.
Do NOT unpack, clean, or pack. Only edit slide XML content.

Rules: edit tool only (no sed), grep first, preserve <a:pPr>.
```

---

## 4. Pack Prompt (pipeline Step 3)

Pack the edited directory into final output.

```
Pack the edited PPT directory into a final file.

pptx scripts: ~/.openclaw/skills/pptx/scripts/
compress script: {workspace}/skills/ppt-from-template/scripts/compress_pptx.py

Steps:
1. Verify slides exist: ls /tmp/ppt-work/unpacked/ppt/slides/
2. Pack: python3 ~/.openclaw/skills/pptx/scripts/office/pack.py /tmp/ppt-work/unpacked/ /tmp/ppt-work/output.pptx --original "{template_path}"
3. Compress: python3 {compress_script} /tmp/ppt-work/output.pptx /tmp/ppt-work/final.pptx
4. Output: mkdir -p {workspace}/output/ && cp /tmp/ppt-work/final.pptx "{output_path}"
5. Report file size and slide count.
6. Cleanup: rm -rf /tmp/ppt-work/
```

---

## Batch Splitting Guide

When splitting slides into batches:
- Target 5-8 slides per batch
- Keep related slides together (e.g. a section header + its content slides)
- Each batch edits different slide XML files — no conflicts possible
- Example: 30 slides → batch 1 (slide1-8), batch 2 (slide9-16), batch 3 (slide17-24), batch 4 (slide25-30)
