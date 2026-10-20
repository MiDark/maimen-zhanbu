#!/usr/bin/env python3
"""把 samples/ming-card-sample.html 渲染成 assets/card-preview.png

macOS 无头 Chrome 的 clientWidth 有 485 的下限，直接开 390 会得到一张 485 宽的图。
所以先按 420 宽度渲染（注入 !important 宽度锁死），再用 Pillow 精确裁掉右侧多出来的部分。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "samples/ming-card-sample.html")
OUT = os.path.join(ROOT, "assets/card-preview.png")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

VIEW_W = 390        # 目标视口宽（移动端基准）
PAD = 2             # 右侧留一点余量，避免裁到描边
PROBE_H = 4200      # 先按很高的窗口渲染，量出真实内容高


def run(html_path, height, out_png, profile):
    subprocess.run([
        CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        f"--user-data-dir={profile}",          # 必须独立 profile，否则和已开的 Chrome 抢锁直接 SIGTRAP
        "--force-device-scale-factor=2",
        "--default-background-color=F5F0E8",
        f"--window-size={VIEW_W + 60},{height}",
        f"--screenshot={out_png}",
        "--virtual-time-budget=2500",
        "file://" + html_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    tmp = tempfile.mkdtemp(prefix="mcdcard")
    # 注入：把 html/body 宽度锁到 390，避免 macOS 下 485 下限把折页撑宽
    src = open(SRC, encoding="utf-8").read()
    lock = (
        "<style>html,body{width:%dpx!important;max-width:%dpx!important;"
        "overflow-x:hidden!important;}</style></head>" % (VIEW_W, VIEW_W)
    )
    src = src.replace("</head>", lock, 1)
    probe = os.path.join(tmp, "probe.html")
    open(probe, "w", encoding="utf-8").write(src)

    shot = os.path.join(tmp, "probe.png")
    run(probe, PROBE_H, shot, os.path.join(tmp, "prof"))
    img = Image.open(shot)
    print("raw:", img.size)

    # 量内容高度：从底部往上找第一行非底色像素
    img = img.convert("RGB")          # ★ 必须留引用，否则 PixelAccess 指向已被回收的临时图
    px = img.load()
    w, h = img.size
    crop_w = min(w, VIEW_W * 2 + PAD)
    # 只在裁切区内找内容：Chrome 截图右下角有几像素的渐变噪点，不排除会把底边顶到窗口底部
    bg = px[1, h - 2]
    bottom = h
    for y in range(h - 1, -1, -1):
        row_has = False
        for x in range(0, crop_w, 3):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 12:
                row_has = True
                break
        if row_has:
            bottom = min(h, y + 14)   # 留 14 逻辑像素下边距（@2x）
            break

    out = img.crop((0, 0, crop_w, bottom))
    out.save(OUT, optimize=True)
    print("saved:", OUT, out.size)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
