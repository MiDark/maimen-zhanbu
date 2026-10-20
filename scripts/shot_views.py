#!/usr/bin/env python3
"""多分辨率截图：验证 4:3 → 2.22:1 各档的显示效果

用法：python scripts/shot_views.py
输出：.tmp_shots/<w>x<h>_<view>.png
"""
import os
import shutil
import subprocess
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web/index.html")
OUTDIR = os.path.join(ROOT, ".tmp_shots")

# (宽, 高, 比例说明)
VIEWPORTS = [
    (390, 844, "phone"),      # iPhone 竖屏基准
    (834, 1194, "tablet"),    # iPad 竖屏
    (1200, 900, "43"),        # 4:3（小红书封面比例）
    (1920, 1080, "169"),      # 16:9
    (3200, 1440, "222"),      # 2.22:1 宽屏
]
VIEWS = ["today", "gua", "store", "me"]


def shot(html_path, w, h, out_png, profile, scale=1):
    subprocess.run([
        CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        f"--user-data-dir={profile}",
        f"--force-device-scale-factor={scale}",
        "--default-background-color=F5F0E8",
        f"--window-size={w},{h}",
        f"--screenshot={out_png}",
        "--virtual-time-budget=3000",
        "file://" + html_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    src = open(SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="mcdview")
    # 把快照 js 一起放进临时目录，保证相对引用 mcd_data.js 能解析
    shutil.copy(os.path.join(ROOT, "web/mcd_data.js"), os.path.join(tmp, "mcd_data.js"))

    for w, h, tag in VIEWPORTS:
        # macOS 无头 Chrome 的 clientWidth 有 ~485 的下限：
        # 窄视口要注入宽度锁，否则截到的是 485 宽排版的前 390px，右侧被裁
        lock = ""
        if w < 485:
            lock = (
                f"<style>html,body{{width:{w}px!important;max-width:{w}px!important;"
                f"overflow-x:hidden!important;}}"
                # 固定定位元素以真实视口（485）为包含块，宽度锁管不住它：
                # 底栏手动钉到 390 宽并居中，否则截图会缺最后一个 Tab（纯截图假象）
                f".tabbar{{left:0!important;right:auto!important;width:{w}px!important;"
                f"margin:0!important;transform:none!important;}}</style></head>"
            )
        for v in VIEWS:
            inject = (
                f"<script>window.addEventListener('load',function(){{"
                f"setTimeout(function(){{window.goView && window.goView('{v}');}},150);"
                f"}});</script></body>"
            )
            page = src.replace("</body>", inject, 1)
            if lock:
                page = page.replace("</head>", lock, 1)
            fpath = os.path.join(tmp, f"view_{tag}_{v}.html")
            open(fpath, "w", encoding="utf-8").write(page)
            out = os.path.join(OUTDIR, f"{tag}_{w}x{h}_{v}.png")
            shot(fpath, w, h, out, os.path.join(tmp, f"prof_{tag}"))
            print("ok", out)
    print("done ->", OUTDIR)


if __name__ == "__main__":
    main()
