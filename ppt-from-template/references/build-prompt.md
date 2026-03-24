# Build Prompt Template

Use this as the `task` parameter for `sessions_spawn`. Replace `{placeholders}` with actual paths.

---

Create a PPT from plan.yaml.

**Paths:**
- plan.yaml: `{workspace}/plan.yaml`
- pptx scripts: `~/.openclaw/skills/pptx/scripts/`
- editing rules: `~/.openclaw/skills/pptx/editing.md`

**Steps:**

1. Read plan.yaml
2. Check disk: `df -h /tmp`
3. Unpack template:
   ```bash
   rm -rf /tmp/ppt-work/ && mkdir -p /tmp/ppt-work/
   python3 ~/.openclaw/skills/pptx/scripts/office/unpack.py "{template_path}" /tmp/ppt-work/unpacked/
   ```
4. Trim slides: in `presentation.xml`, keep only `<p:sldId>` entries for slides listed in plan's `source` fields. Remove all others.
5. Duplicate slides: if the same source appears multiple times in plan, copy the slide XML and update `presentation.xml` and `_rels/`.
6. Reorder slides to match plan sequence.
7. Clean orphaned files:
   ```bash
   python3 ~/.openclaw/skills/pptx/scripts/clean.py /tmp/ppt-work/unpacked/
   ```
8. Edit each slide:
   - `grep` to locate placeholder text in the slide XML
   - Use `edit` tool for precise text replacement (not sed)
   - Preserve all `<a:pPr>` formatting attributes
   - For multi-item content, use separate `<a:p>` elements
9. Pack:
   ```bash
   python3 ~/.openclaw/skills/pptx/scripts/office/pack.py \
     /tmp/ppt-work/unpacked/ /tmp/ppt-work/output.pptx \
     --original "{template_path}"
   ```
10. Compress (optional):
    ```bash
    python3 {workspace}/skills/ppt-from-template/scripts/compress_pptx.py \
      /tmp/ppt-work/output.pptx /tmp/ppt-work/final.pptx
    ```
11. Move to output:
    ```bash
    mkdir -p {workspace}/output/
    cp /tmp/ppt-work/final.pptx "{output_path}"
    ```
12. Cleanup: `rm -rf /tmp/ppt-work/`

**Rules:**
- Use `edit` tool for all text modifications, never `sed`
- Chinese quotes → XML entities: `&#x201C;` `&#x201D;`
- Preserve `<a:pPr>` format attributes
- Multi-item lists → multiple `<a:p>` elements
- Always `grep` first, then `edit` — never `read` entire slide XML
