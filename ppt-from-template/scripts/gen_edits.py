#!/usr/bin/env python3
"""
gen_edits.py v2 — XML-semantic edit generator for PPT slides

Parses slide XML with ElementTree to extract shapes with:
- Position coordinates (x, y) for visual ordering
- Font size for title/body heuristics
- Paragraph-level text for reliable matching

Matches plan.yaml content to shapes using:
- Font size (largest = title)
- Position (top→bottom, left→right)
- Paragraph count (multi-para = items list)
- Role hints from plan.yaml

Output edits.json format:
{
  "slide1.xml": [
    {"type": "text",  "match": ["旧标题"],     "replace": "新标题"},
    {"type": "items", "match": ["项1","项2"],   "replace": ["新1","新2","新3"]}
  ]
}
"""

import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import yaml

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def extract_shapes(xml_path):
    """Extract text shapes with position, font size, and paragraph text."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    shapes = []

    for sp in root.iter("{%s}sp" % NS["p"]):
        txBody = sp.find("{%s}txBody" % NS["p"])
        if txBody is None:
            continue

        # Position
        x, y = 0, 0
        off = sp.find(".//{%s}off" % NS["a"])
        if off is not None:
            x = int(off.get("x", "0"))
            y = int(off.get("y", "0"))

        # Max font size (from rPr or defRPr)
        max_font = 0
        for tag in ("rPr", "defRPr"):
            for el in txBody.iter("{%s}%s" % (NS["a"], tag)):
                sz = el.get("sz")
                if sz:
                    max_font = max(max_font, int(sz))

        # Paragraph texts
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

        if not paragraphs:
            continue

        shapes.append(
            {
                "x": x,
                "y": y,
                "font_size": max_font,
                "paragraphs": paragraphs,
            }
        )

    shapes.sort(key=lambda s: (s["y"], s["x"]))
    return shapes


def match_content_to_shapes(shapes, content, role=None):
    """Match plan content fields to shapes using font + position heuristics."""
    if not content or not shapes:
        return []

    edits = []
    used = set()

    def _largest_font():
        best_i, best_sz = -1, -1
        for i, s in enumerate(shapes):
            if i not in used and s["font_size"] > best_sz:
                best_i, best_sz = i, s["font_size"]
        return best_i

    def _second_font():
        """Second-largest font (for subtitle)."""
        first = _largest_font()
        best_i, best_sz = -1, -1
        for i, s in enumerate(shapes):
            if i not in used and i != first and s["font_size"] > best_sz:
                best_i, best_sz = i, s["font_size"]
        return best_i

    def _next_unused():
        for i in range(len(shapes)):
            if i not in used:
                return i
        return -1

    def _multi_para():
        for i, s in enumerate(shapes):
            if i not in used and len(s["paragraphs"]) >= 2:
                return i
        return -1

    def _flatten_value(v):
        """Convert any value to display string. Handles dicts, lists, etc."""
        if isinstance(v, dict):
            # e.g. {"name": "Gateway", "pct": "消息路由"} → "Gateway — 消息路由"
            parts = [str(val) for val in v.values()]
            return " — ".join(parts)
        return str(v)

    def _add_edit(idx, field_name, field_value):
        if idx < 0:
            return
        used.add(idx)
        if field_name in ("items", "categories") or (
            isinstance(field_value, list) and field_name != "keywords"
        ):
            edits.append(
                {
                    "type": "items",
                    "match": shapes[idx]["paragraphs"],
                    "replace": [_flatten_value(v) for v in field_value],
                }
            )
        else:
            text = (
                " | ".join(_flatten_value(v) for v in field_value)
                if isinstance(field_value, list)
                else _flatten_value(field_value)
            )
            edits.append(
                {"type": "text", "match": shapes[idx]["paragraphs"], "replace": text}
            )

    # --- ordered field matching ---

    # 1. Title / main_title → largest font
    for key in ("main_title", "title"):
        if key in content:
            _add_edit(_largest_font(), key, content[key])
            break

    # 2. Subtitle → second-largest font or next unused
    if "subtitle" in content:
        i = _second_font()
        if i < 0:
            i = _next_unused()
        _add_edit(i, "subtitle", content["subtitle"])

    # 3. Keywords → next unused, joined as text
    if "keywords" in content:
        _add_edit(_next_unused(), "keywords", content["keywords"])

    # 4. Body → next unused
    if "body" in content:
        _add_edit(_next_unused(), "body", content["body"])

    # 5. Items → prefer multi-para shape
    if "items" in content:
        i = _multi_para()
        if i < 0:
            i = _next_unused()
        _add_edit(i, "items", content["items"])

    # 6. Remaining fields
    handled = {"title", "main_title", "subtitle", "body", "items", "keywords", "categories"}
    for key, val in content.items():
        if key not in handled:
            _add_edit(_next_unused(), key, val)

    # 7. Clear unedited shapes (remove stale template text)
    for i, s in enumerate(shapes):
        if i not in used:
            edits.append(
                {"type": "clear", "match": s["paragraphs"]}
            )

    return edits


def main():
    if len(sys.argv) < 4:
        print(
            "用法: python3 gen_edits.py <unpacked_dir> <plan_yaml> <output_edits_json>"
        )
        sys.exit(1)

    unpacked_dir = sys.argv[1]
    plan_path = sys.argv[2]
    output_path = sys.argv[3]
    slides_dir = os.path.join(unpacked_dir, "ppt/slides")

    with open(plan_path) as f:
        plan = yaml.safe_load(f)

    all_edits = {}
    total_edits = 0

    for idx, slide_plan in enumerate(plan.get("slides", [])):
        slide_num = idx + 1
        slide_file = f"slide{slide_num}.xml"
        xml_path = os.path.join(slides_dir, slide_file)

        if not os.path.exists(xml_path):
            print(f"  ⚠️  {slide_file}: 不存在")
            continue

        content = slide_plan.get("content", {})
        if not content:
            print(f"  ⏭️  {slide_file}: 无 content")
            continue

        role = slide_plan.get("role")
        shapes = extract_shapes(xml_path)
        if not shapes:
            print(f"  ⏭️  {slide_file}: 无文本形状")
            continue

        edits = match_content_to_shapes(shapes, content, role)
        if edits:
            all_edits[slide_file] = edits
            total_edits += len(edits)
            print(
                f"  📝 {slide_file}: {len(edits)} edits "
                f"({len(shapes)} shapes, role={role})"
            )
        else:
            print(f"  ⏭️  {slide_file}: 无匹配")

    with open(output_path, "w") as f:
        json.dump(all_edits, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {output_path}: {len(all_edits)} slides, {total_edits} edits")


if __name__ == "__main__":
    main()
