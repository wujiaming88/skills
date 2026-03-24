#!/usr/bin/env python3
"""
apply_edits.py v2 — XML-semantic slide editor for PPT

Operates on slide XML via ElementTree:
- "text" edits: merges all <a:r> in target <a:p> into one, replaces text
- "items" edits: restructures <a:p> list (add/remove paragraphs), preserving style

Usage:
  python3 apply_edits.py <unpacked_dir> <edits_json> [slide1.xml ...] [--dry-run]
"""

import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

# Register namespaces to avoid ns0/ns1 prefixes in output
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)
# Also register common namespaces used in PPTX
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
ET.register_namespace("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006")
ET.register_namespace("v", "urn:schemas-microsoft-com:vml")


def get_shape_text(txBody):
    """Get paragraphs text from a txBody element."""
    paragraphs = []
    for p_el in txBody.findall("{%s}p" % NS["a"]):
        texts = []
        for r_el in p_el.findall("{%s}r" % NS["a"]):
            t_el = r_el.find("{%s}t" % NS["a"])
            if t_el is not None and t_el.text:
                texts.append(t_el.text)
        para = "".join(texts).strip()
        if para:
            paragraphs.append(para)
    return paragraphs


def find_target_shape(root, match_paragraphs):
    """Find the <p:sp> whose txBody paragraphs match the given list."""
    for sp in root.iter("{%s}sp" % NS["p"]):
        txBody = sp.find("{%s}txBody" % NS["p"])
        if txBody is None:
            continue
        paras = get_shape_text(txBody)
        if paras == match_paragraphs:
            return sp, txBody
    # Fallback: partial match (first N paragraphs match)
    for sp in root.iter("{%s}sp" % NS["p"]):
        txBody = sp.find("{%s}txBody" % NS["p"])
        if txBody is None:
            continue
        paras = get_shape_text(txBody)
        if len(paras) > 0 and len(match_paragraphs) > 0 and paras[0] == match_paragraphs[0]:
            return sp, txBody
    return None, None


def apply_text_edit(txBody, new_text):
    """Replace all text in txBody with new_text.

    Strategy: find paragraphs with text, replace first one, remove rest.
    If multiple a:r in a paragraph, merge into first a:r.
    """
    a_p = "{%s}p" % NS["a"]
    a_r = "{%s}r" % NS["a"]
    a_t = "{%s}t" % NS["a"]

    # Find paragraphs that have text runs
    text_paras = []
    for p_el in txBody.findall(a_p):
        runs = p_el.findall(a_r)
        has_text = any(
            r.find(a_t) is not None and r.find(a_t).text and r.find(a_t).text.strip()
            for r in runs
        )
        if has_text:
            text_paras.append(p_el)

    if not text_paras:
        return False

    # Put all text into first text paragraph
    first_p = text_paras[0]
    runs = first_p.findall(a_r)
    if runs:
        # Keep first run, set text, remove rest
        runs[0].find(a_t).text = new_text
        for r in runs[1:]:
            first_p.remove(r)
    else:
        return False

    # Remove remaining text paragraphs (keep non-text ones)
    for p_el in text_paras[1:]:
        txBody.remove(p_el)

    return True


def apply_items_edit(txBody, new_items):
    """Replace paragraph list with new_items, preserving style.

    Strategy:
    - Find existing text paragraphs
    - Use first one as template for style (a:pPr, a:rPr)
    - Create N paragraphs for N items
    - Replace the old paragraph list
    """
    a_p = "{%s}p" % NS["a"]
    a_r = "{%s}r" % NS["a"]
    a_t = "{%s}t" % NS["a"]
    a_pPr = "{%s}pPr" % NS["a"]
    a_rPr = "{%s}rPr" % NS["a"]

    # Find existing text paragraphs and their positions
    all_children = list(txBody)
    text_paras = []
    text_para_indices = []
    for i, child in enumerate(all_children):
        if child.tag == a_p:
            runs = child.findall(a_r)
            has_text = any(
                r.find(a_t) is not None
                and r.find(a_t).text
                and r.find(a_t).text.strip()
                for r in runs
            )
            if has_text:
                text_paras.append(child)
                text_para_indices.append(i)

    if not text_paras:
        return False

    # Clone first text para as template
    template_p = text_paras[0]
    template_pPr = template_p.find(a_pPr)
    template_runs = template_p.findall(a_r)
    template_rPr = None
    if template_runs:
        template_rPr = template_runs[0].find(a_rPr)

    # Build new paragraphs
    new_paras = []
    for item_text in new_items:
        new_p = ET.SubElement(ET.Element("dummy"), a_p)
        if template_pPr is not None:
            new_p.append(copy.deepcopy(template_pPr))
        new_r = ET.SubElement(new_p, a_r)
        if template_rPr is not None:
            new_r.append(copy.deepcopy(template_rPr))
        new_t = ET.SubElement(new_r, a_t)
        new_t.text = item_text
        new_paras.append(new_p)

    # Remove old text paragraphs
    for p_el in text_paras:
        txBody.remove(p_el)

    # Insert new paragraphs at position of first old text paragraph
    insert_pos = text_para_indices[0] if text_para_indices else len(list(txBody))
    for i, new_p in enumerate(new_paras):
        txBody.insert(insert_pos + i, new_p)

    return True


def clear_shape_text(txBody):
    """Remove all text from a shape's txBody, keeping one empty paragraph."""
    a_p = "{%s}p" % NS["a"]
    a_r = "{%s}r" % NS["a"]
    a_t = "{%s}t" % NS["a"]

    text_paras = []
    for p_el in txBody.findall(a_p):
        runs = p_el.findall(a_r)
        has_text = any(
            r.find(a_t) is not None and r.find(a_t).text and r.find(a_t).text.strip()
            for r in runs
        )
        if has_text:
            text_paras.append(p_el)

    if not text_paras:
        return False

    # Keep first paragraph as empty placeholder (OOXML requires ≥1 <a:p>)
    first_p = text_paras[0]
    a_r = "{%s}r" % NS["a"]
    for r in first_p.findall(a_r):
        first_p.remove(r)

    # Remove remaining text paragraphs
    for p_el in text_paras[1:]:
        txBody.remove(p_el)

    return True


def process_slide(slide_path, edits, dry_run=False):
    """Apply edits to a single slide XML file."""
    tree = ET.parse(slide_path)
    root = tree.getroot()

    applied = 0
    missed = 0

    for edit in edits:
        match_paras = edit["match"]
        edit_type = edit.get("type", "text")

        sp, txBody = find_target_shape(root, match_paras)
        if txBody is None:
            missed += 1
            preview = match_paras[0][:50] if match_paras else "?"
            print(f"    ❌ 未匹配: {preview}...")
            continue

        if dry_run:
            applied += 1
            print(f"    📝 [DRY] {edit_type}: {match_paras[0][:40]}... → {str(edit['replace'])[:40]}...")
            continue

        if edit_type == "clear":
            if not dry_run:
                ok = clear_shape_text(txBody)
            else:
                ok = True
                print(f"    🗑️ [DRY] clear: {match_paras[0][:40]}...")
            if ok:
                applied += 1
            else:
                missed += 1
        elif edit_type == "items":
            ok = apply_items_edit(txBody, edit["replace"])
        else:
            ok = apply_text_edit(txBody, edit["replace"])

        if ok:
            applied += 1
        else:
            missed += 1
            print(f"    ⚠️  替换失败: {match_paras[0][:50]}...")

    if not dry_run and applied > 0:
        tree.write(slide_path, xml_declaration=True, encoding="UTF-8")

    return applied, missed


def main():
    if len(sys.argv) < 3:
        print(
            "用法: python3 apply_edits.py <unpacked_dir> <edits_json> "
            "[slide1.xml ...] [--dry-run]"
        )
        sys.exit(1)

    unpacked_dir = sys.argv[1]
    edits_json_path = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    slide_filter = set()
    for arg in sys.argv[3:]:
        if arg != "--dry-run":
            slide_filter.add(arg)
    slide_filter = slide_filter or None

    with open(edits_json_path) as f:
        all_edits = json.load(f)

    slides_dir = os.path.join(unpacked_dir, "ppt/slides")
    total_applied = 0
    total_missed = 0

    print("=" * 50)
    print(f"apply_edits.py v2 {'[DRY RUN]' if dry_run else ''}")
    print("=" * 50)

    for slide_file, edits in sorted(all_edits.items()):
        if slide_filter and slide_file not in slide_filter:
            continue

        slide_path = os.path.join(slides_dir, slide_file)
        if not os.path.exists(slide_path):
            print(f"  ⚠️  {slide_file}: 不存在")
            continue

        applied, missed = process_slide(slide_path, edits, dry_run)
        total_applied += applied
        total_missed += missed

        icon = "✅" if missed == 0 else "⚠️ "
        print(f"  {icon} {slide_file}: {applied}/{len(edits)} 成功")

    print(f"\n{'=' * 50}")
    print(f"完成! 成功 {total_applied}, 失败 {total_missed}")
    if total_missed:
        print(f"⚠️  {total_missed} 处需手动处理")
    print("=" * 50)

    sys.exit(1 if total_missed > 0 else 0)


if __name__ == "__main__":
    main()
