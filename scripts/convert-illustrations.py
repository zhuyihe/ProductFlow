"""
Atelier R4 插画批量转换脚本：PNG → WebP + AVIF（1x spec + 2x 源图尺寸）

策略：
- 1x：缩到 PRD spec 尺寸（Lanczos 高质重采样）
- 2x：用源图原始尺寸输出（避免放大失真；浏览器 srcset 自适应）
- WebP：quality=80（PRD 推荐）
- AVIF：quality=65（视觉相当 WebP 80）

跳过的图：404.png、desktop-only.png（用户将重新生成）
"""

import os
import sys
from PIL import Image
import pillow_avif  # noqa: F401  注册 AVIF 编码器

SRC_DIR = r"D:\netcup\ProductFlow\images"
DST_DIR = r"D:\netcup\ProductFlow\web\public\illustrations"

# 仅集成本次 6 张（404 + desktop-only 用户重生）
TARGETS = {
    "logo-mark.png":           (1024, 1024),  # 1x spec (favicon raster fallback)
    "login-hero.png":          (1024, 1280),
    "gallery-empty.png":       (800, 800),
    "productlist-empty.png":   (800, 800),
    "generic-empty.png":       (600, 600),
    "success-celebration.png": (600, 600),
}

WEBP_Q = 80
AVIF_Q = 65


def to_size(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Lanczos 高质重采样到目标尺寸。"""
    return img.resize(target, Image.Resampling.LANCZOS)


def export(img: Image.Image, out_base: str) -> tuple[int, int]:
    """输出 WebP + AVIF 一对，返回字节数 (webp_bytes, avif_bytes)。"""
    webp_path = out_base + ".webp"
    avif_path = out_base + ".avif"
    img.save(webp_path, "WEBP", quality=WEBP_Q, method=6)
    img.save(avif_path, "AVIF", quality=AVIF_Q, speed=4)
    return os.path.getsize(webp_path), os.path.getsize(avif_path)


def main() -> int:
    os.makedirs(DST_DIR, exist_ok=True)
    print(f"{'file':<26} {'1x dims':<14} {'2x dims':<14} {'webp@1x':<10} {'avif@1x':<10} {'webp@2x':<10} {'avif@2x':<10}")
    print("-" * 100)
    for fn, spec_1x in TARGETS.items():
        src = os.path.join(SRC_DIR, fn)
        if not os.path.exists(src):
            print(f"!! MISSING: {fn}", file=sys.stderr)
            return 1
        stem = os.path.splitext(fn)[0]
        img = Image.open(src).convert("RGB")

        # 1x: spec
        img_1x = to_size(img, spec_1x)
        out_1x = os.path.join(DST_DIR, stem)
        w1, a1 = export(img_1x, out_1x)

        # 2x: 源图原始尺寸（不放大）
        src_w, src_h = img.size
        out_2x = os.path.join(DST_DIR, f"{stem}@2x")
        w2, a2 = export(img, out_2x)

        print(
            f"{fn:<26} {spec_1x[0]}x{spec_1x[1]:<10} {src_w}x{src_h:<10} "
            f"{w1//1024:>6} KB  {a1//1024:>6} KB  {w2//1024:>6} KB  {a2//1024:>6} KB"
        )

    print("-" * 100)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
