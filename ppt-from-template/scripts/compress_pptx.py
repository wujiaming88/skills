#!/usr/bin/env python3
"""Compress a PPTX file by re-compressing ZIP contents and optimizing images.

Usage:
    python compress_pptx.py input.pptx output.pptx [--quality 85] [--no-image-optimize]

For large files (500MB+), this can reduce size by 10-60% depending on content.
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

def compress_pptx(input_path: str, output_path: str, jpeg_quality: int = 85, optimize_images: bool = True):
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"Error: {input_file} does not exist", file=sys.stderr)
        sys.exit(1)

    original_size = input_file.stat().st_size
    print(f"Input:  {input_file} ({_fmt_size(original_size)})")

    image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    optimized_count = 0
    total_files = 0
    skipped_count = 0

    # Try to import Pillow for image optimization
    pil_available = False
    if optimize_images:
        try:
            from PIL import Image
            pil_available = True
        except ImportError:
            print("Warning: Pillow not installed, skipping image optimization")
            print("  Install with: pip install Pillow")

    with zipfile.ZipFile(input_file, 'r') as zin:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            for item in zin.infolist():
                total_files += 1
                data = zin.read(item.filename)

                # Optimize images if Pillow is available
                if pil_available and optimize_images:
                    ext = Path(item.filename).suffix.lower()
                    if ext in image_exts:
                        try:
                            optimized_data = _optimize_image(data, ext, jpeg_quality)
                            if optimized_data and len(optimized_data) < len(data):
                                data = optimized_data
                                optimized_count += 1
                            else:
                                skipped_count += 1
                        except Exception as e:
                            skipped_count += 1

                # Write with maximum compression
                zout.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    compressed_size = output_file.stat().st_size
    reduction = original_size - compressed_size
    pct = (reduction / original_size * 100) if original_size > 0 else 0

    print(f"Output: {output_file} ({_fmt_size(compressed_size)})")
    print(f"Saved:  {_fmt_size(reduction)} ({pct:.1f}% reduction)")
    print(f"Files:  {total_files} total, {optimized_count} images optimized, {skipped_count} skipped")


def _optimize_image(data: bytes, ext: str, jpeg_quality: int) -> bytes | None:
    """Optimize image data, return compressed bytes or None if failed."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))

    buf = io.BytesIO()

    if ext in {'.jpg', '.jpeg'}:
        # Re-save JPEG with specified quality
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
    elif ext == '.png':
        # Re-save PNG with optimization
        img.save(buf, format='PNG', optimize=True)
    elif ext in {'.bmp', '.tiff', '.tif'}:
        # Convert BMP/TIFF to PNG (much smaller)
        if img.mode == 'RGBA':
            img.save(buf, format='PNG', optimize=True)
        else:
            img = img.convert('RGB')
            img.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
    else:
        return None

    return buf.getvalue()


def _fmt_size(size: int) -> str:
    """Format byte size to human readable."""
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024**3):.1f} GB"
    elif size >= 1024 * 1024:
        return f"{size / (1024**2):.1f} MB"
    elif size >= 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size} B"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compress PPTX file')
    parser.add_argument('input', help='Input .pptx file')
    parser.add_argument('output', help='Output compressed .pptx file')
    parser.add_argument('--quality', type=int, default=85, help='JPEG quality (1-100, default: 85)')
    parser.add_argument('--no-image-optimize', action='store_true', help='Skip image optimization')
    args = parser.parse_args()

    compress_pptx(args.input, args.output, args.quality, not args.no_image_optimize)
