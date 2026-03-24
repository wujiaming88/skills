#!/usr/bin/env python3
"""
fix_rels.py - 修复 PPTX 解包后的关系引用问题

用途：Prep 阶段复制 slide 后、Pack 阶段打包前，自动清理失效引用。

处理的问题：
1. rels 文件中指向不存在文件的 Relationship（broken refs）
2. 复制页共享 notesSlides 导致的多对一引用
3. slide XML 中引用了被删 rels ID 的 <tags>、<blip>、<p:tags> 元素

用法：
  python3 fix_rels.py <unpacked_dir>

示例：
  python3 fix_rels.py /tmp/ppt-work/unpacked
"""

import os
import re
import sys
import glob


def get_valid_rids(rels_file):
    """从 rels 文件提取所有有效的 rId"""
    with open(rels_file, 'r') as f:
        content = f.read()
    return set(re.findall(r'Id="(rId\d+)"', content))


def fix_broken_rels(unpacked_dir):
    """删除 rels 文件中指向不存在文件的 Relationship"""
    slides_dir = os.path.join(unpacked_dir, "ppt/slides")
    rels_dir = os.path.join(slides_dir, "_rels")
    
    if not os.path.exists(rels_dir):
        return 0
    
    total_removed = 0
    
    for rels_file in glob.glob(os.path.join(rels_dir, "*.xml.rels")):
        with open(rels_file, 'r') as f:
            content = f.read()
        
        original = content
        removed = 0
        
        # 找所有 Relationship 的 Target
        for m in re.finditer(r'<[\w:]*Relationship[^>]*Target="([^"]+)"[^>]*/>', content):
            target = m.group(1)
            full_path = os.path.normpath(os.path.join(slides_dir, target))
            if not os.path.exists(full_path):
                content = content.replace(m.group(0), '')
                removed += 1
        
        if removed > 0:
            with open(rels_file, 'w') as f:
                f.write(content)
            total_removed += removed
            print(f"  {os.path.basename(rels_file)}: 删除 {removed} 个 broken refs")
    
    return total_removed


def fix_shared_notes(unpacked_dir):
    """删除复制页（*_b, *_c 等）的 notesSlides 引用，避免多对一"""
    rels_dir = os.path.join(unpacked_dir, "ppt/slides/_rels")
    
    if not os.path.exists(rels_dir):
        return 0
    
    total_removed = 0
    
    # 只处理带后缀的复制页
    for rels_file in glob.glob(os.path.join(rels_dir, "*_*.xml.rels")):
        with open(rels_file, 'r') as f:
            content = f.read()
        
        original = content
        content = re.sub(
            r'<[\w:]*Relationship[^>]*Target="[^"]*notesSlides[^"]*"[^>]*/>',
            '', content
        )
        
        if content != original:
            with open(rels_file, 'w') as f:
                f.write(content)
            total_removed += 1
            print(f"  {os.path.basename(rels_file)}: 删除 notes 引用")
    
    return total_removed


def fix_orphan_rid_refs(unpacked_dir):
    """清理 slide XML 中引用了不存在 rId 的元素"""
    slides_dir = os.path.join(unpacked_dir, "ppt/slides")
    rels_dir = os.path.join(slides_dir, "_rels")
    
    if not os.path.exists(rels_dir):
        return 0
    
    total_fixed = 0
    
    for slide_xml in glob.glob(os.path.join(slides_dir, "slide*.xml")):
        basename = os.path.basename(slide_xml)
        rels_file = os.path.join(rels_dir, basename + ".rels")
        
        if not os.path.exists(rels_file):
            continue
        
        valid_ids = get_valid_rids(rels_file)
        
        with open(slide_xml, 'r') as f:
            content = f.read()
        
        original = content
        
        # 删除 <p:tags r:id="rIdX"/> 引用无效 rId
        def remove_invalid_tags(m):
            rid = re.search(r'r:id="(rId\d+)"', m.group(0))
            if rid and rid.group(1) not in valid_ids:
                return ''
            return m.group(0)
        
        content = re.sub(r'<[\w:]*tags\s[^/]*/>', remove_invalid_tags, content)
        
        # 删除 <a:blip> 中无效的 r:embed 属性
        def fix_invalid_blip(m):
            rid = re.search(r'r:embed="(rId\d+)"', m.group(0))
            if rid and rid.group(1) not in valid_ids:
                return re.sub(r'\s*r:embed="rId\d+"', '', m.group(0))
            return m.group(0)
        
        content = re.sub(r'<a:blip[^>]*>', fix_invalid_blip, content)
        
        if content != original:
            with open(slide_xml, 'w') as f:
                f.write(content)
            total_fixed += 1
            print(f"  {basename}: 清理无效 rId 引用")
    
    return total_fixed


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fix_rels.py <unpacked_dir>")
        sys.exit(1)
    
    unpacked_dir = sys.argv[1]
    
    if not os.path.isdir(unpacked_dir):
        print(f"错误: {unpacked_dir} 不是目录")
        sys.exit(1)
    
    print("=" * 50)
    print("fix_rels.py - 修复 PPTX 关系引用")
    print("=" * 50)
    
    print("\n[1/3] 删除 broken refs...")
    broken = fix_broken_rels(unpacked_dir)
    
    print("\n[2/3] 清理复制页 notes 引用...")
    notes = fix_shared_notes(unpacked_dir)
    
    print("\n[3/3] 清理 slide XML 中的无效 rId...")
    orphan = fix_orphan_rid_refs(unpacked_dir)
    
    total = broken + notes + orphan
    print(f"\n{'=' * 50}")
    print(f"完成! 共修复 {total} 处问题")
    print(f"  broken refs: {broken}")
    print(f"  shared notes: {notes}")
    print(f"  orphan rIds: {orphan}")
    print(f"{'=' * 50}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
