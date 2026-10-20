#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「网页版」二维码 PNG（小工具离线包里用，打包时内联成 data URI）。

小工具容器禁联网、禁跳外链、禁剪贴板，唯一能把人送到网页版的路径是**扫码**：
  - 页面里直接显示二维码，另一台手机扫；
  - 或「存二维码到相册」，再用微信「扫一扫 → 相册」识别。

用法：
    python3 scripts/make_qr.py                       # 默认 GitHub Pages 地址
    python3 scripts/make_qr.py --url https://...     # 换地址
产物：
    minitool/assets/qr-web.png   （供 build_minitool.py 内联）
"""

import argparse
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "minitool" / "assets" / "qr-web.png"
DEFAULT_URL = "https://midark.github.io/maimen-zhanbu/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--box", type=int, default=10, help="每个模块的像素数")
    ap.add_argument("--border", type=int, default=3, help="静区模块数（>=2）")
    a = ap.parse_args()

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=a.box, border=a.border)
    qr.add_data(a.url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=(17, 17, 17), back_color=(255, 253, 248)).convert("RGB")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"✓ {OUT.relative_to(ROOT)}  {img.size[0]}×{img.size[1]}  "
          f"{OUT.stat().st_size} 字节  内容={a.url}")


if __name__ == "__main__":
    main()
