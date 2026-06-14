#!/usr/bin/env python3
"""
小红书封面/配图渲染器 — 浏览器无关方案 (WeasyPrint + poppler)。

为什么不用 Playwright/Chromium:
    本宿主机所有 chromium 变体启动即被 sandbox/资源限制杀掉
    (Network service crashed / zygote Socket closed)。第一性原理:
    skill 真正需要的是「HTML(中文+CSS+视觉IP) → 文字清晰的高清竖版 PNG」,
    而非"chromium 能跑"。WeasyPrint(纯 Python)渲染 HTML/CSS→PDF,
    poppler 的 pdftocairo 再栅格化成 PNG,全程无浏览器、无子进程被杀风险。

清晰度: 默认 3x 超采样(在 288 DPI 等效下渲染再 LANCZOS 缩回 1080×1440),
        中文/数字边缘锐利,优于直接 96dpi 出图。

用法:
    python3 render_cover.py <input.html> [output.png] [--width 1080] [--height 1440] [--scale 3] [--jpeg]

默认:
    - 竖版 1080×1440 (小红书 3:4 封面)
    - 3x 超采样高清
    - >5MB 自动转 JPEG (或 --jpeg 强制)
    - 末尾打印 MEDIA:<绝对路径>
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="小红书封面渲染 (WeasyPrint + poppler)")
    ap.add_argument("html", help="HTML 文件路径或 file:// / http(s) URL")
    ap.add_argument("output", nargs="?", default=None, help="输出路径(默认同名 .png)")
    ap.add_argument("--width", type=int, default=1080, help="目标宽 px(默认 1080)")
    ap.add_argument("--height", type=int, default=1440, help="目标高 px(默认 1440,3:4)")
    ap.add_argument("--scale", type=int, default=3, help="超采样倍数(默认 3,越大越清晰越慢)")
    ap.add_argument("--jpeg", action="store_true", help="强制输出 JPEG(quality 92)")
    args = ap.parse_args()

    # --- 解析输入 ---
    html_arg = args.html
    base_url = None
    if html_arg.startswith(("http://", "https://", "file://")):
        from urllib.request import urlopen
        src_kwargs = {"url": html_arg}
    else:
        p = Path(html_arg).resolve()
        if not p.exists():
            print(f"ERROR: 找不到 {p}", file=sys.stderr)
            sys.exit(1)
        # 读为字符串以便清理空占位符块;base_url 指向文件目录让 brand.css/图片相对路径可解析
        import re as _re
        raw = p.read_text(encoding="utf-8")
        # 自动隐藏"仍残留未填充 {{...}} 占位符"的 .point / .stat 卡片块,避免渲出空卡片
        raw = _re.sub(r'<div class="point"[^>]*>(?:(?!</div></div></div>).)*\{\{[^}]*\}\}(?:(?!</div></div></div>).)*</div></div></div>', '', raw, flags=_re.S)
        raw = _re.sub(r'<div class="stat"[^>]*>(?:(?!</div>).)*\{\{[^}]*\}\}(?:(?!</div>).)*</div>\s*</div>', '', raw, flags=_re.S)
        src_kwargs = {"string": raw}
        base_url = str(p.parent) + "/"

    out = args.output or (Path(args.html).with_suffix(".jpg" if args.jpeg else ".png").name)
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from weasyprint import HTML, CSS
    except ImportError:
        print("ERROR: 需要 weasyprint。pip install weasyprint", file=sys.stderr)
        sys.exit(1)

    # --- 注入 @page,锁定页面物理尺寸 = 目标像素(在 96dpi 基准下 1px=1px) ---
    # 模板 body 已是 1080×1440px;这里确保 PDF 单页且无白边。
    page_css = CSS(string=f"""
        @page {{ size: {args.width}px {args.height}px; margin: 0; background: #0E1116; }}
        html, body {{ margin: 0 !important; padding: 0 !important; }}
        body {{ width: {args.width}px; min-height: {args.height}px; }}
    """)

    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "cover.pdf"
        HTML(**src_kwargs, base_url=base_url).write_pdf(
            str(pdf_path), stylesheets=[page_css]
        )

        # --- 超采样栅格化: 基准 96dpi → scale 倍 DPI ---
        dpi = 96 * args.scale
        ppm_base = Path(td) / "raster"
        try:
            subprocess.run(
                ["pdftocairo", "-png", "-r", str(dpi), "-singlefile",
                 str(pdf_path), str(ppm_base)],
                check=True, capture_output=True,
            )
        except FileNotFoundError:
            print("ERROR: 需要 poppler 的 pdftocairo。apt-get install -y poppler-utils", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: pdftocairo 失败: {e.stderr.decode(errors='ignore')}", file=sys.stderr)
            sys.exit(1)

        raster_png = ppm_base.with_suffix(".png")

        # --- 下采样回目标尺寸(LANCZOS),锐利抗锯齿 ---
        from PIL import Image
        img = Image.open(raster_png).convert("RGB")
        if img.size != (args.width, args.height):
            img = img.resize((args.width, args.height), Image.LANCZOS)

        png_out = out.with_suffix(".png")
        img.save(png_out, "PNG", optimize=True)

    # --- 大小管理: >5MB 或 --jpeg 转 JPEG ---
    final = png_out
    size_mb = png_out.stat().st_size / 1024 / 1024
    if args.jpeg or size_mb > 5:
        from PIL import Image
        jpg = out.with_suffix(".jpg")
        Image.open(png_out).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
        if args.jpeg and png_out != jpg:
            png_out.unlink(missing_ok=True)
        final = jpg

    print(f"OK: {final} ({final.stat().st_size/1024/1024:.2f} MB)")
    print(f"MEDIA:{final.resolve()}")


if __name__ == "__main__":
    main()
