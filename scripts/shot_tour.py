#!/usr/bin/env python3
"""把四页拼成一张 README 首图 assets/app-tour.png

4 个视图（今日/卦象/门店/我的）各截 390×844 @2x，铺在纸桌上横排。
"""
import importlib.util
import os
import shutil
import tempfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/app-tour.png")

spec = importlib.util.spec_from_file_location("sv", os.path.join(ROOT, "scripts/shot_views.py"))
sv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sv)

VIEWS = [("today", "今日"), ("gua", "卦象"), ("store", "门店"), ("me", "我的")]
W, H = 390, 844
GAP = 36
PAD = 44


def main():
    src = open(sv.SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="mcdtour")
    shutil.copy(os.path.join(ROOT, "web/mcd_data.js"), os.path.join(tmp, "mcd_data.js"))
    lock = (f"<style>html,body{{width:{W}px!important;max-width:{W}px!important;"
            f"overflow-x:hidden!important;}}"
            f".tabbar{{left:0!important;right:auto!important;width:{W}px!important;"
            f"margin:0!important;transform:none!important;}}</style></head>")

    panels = []
    for v, _name in VIEWS:
        inject = (f"<script>window.addEventListener('load',function(){{"
                  f"setTimeout(function(){{window.goView && window.goView('{v}');}},150);"
                  f"}});</script></body>")
        page = src.replace("</body>", inject, 1).replace("</head>", lock, 1)
        fpath = os.path.join(tmp, f"p_{v}.html")
        open(fpath, "w", encoding="utf-8").write(page)
        png = os.path.join(tmp, f"p_{v}.png")
        sv.shot(fpath, W, H, png, os.path.join(tmp, "prof"), scale=2)
        panels.append(Image.open(png).convert("RGB"))

    pw, ph = panels[0].size          # 780×1688（@2x）
    sw, sh = pw // 2, ph // 2        # 缩回 1x 逻辑尺寸再拼
    panels = [p.resize((sw, sh), Image.LANCZOS) for p in panels]

    cw = PAD * 2 + sw * 4 + GAP * 3
    ch = PAD * 2 + sh
    canvas = Image.new("RGB", (cw, ch), (239, 233, 220))   # 桌面纸色
    for i, p in enumerate(panels):
        x = PAD + i * (sw + GAP)
        canvas.paste(p, (x, PAD))
    canvas.save(OUT, optimize=True)
    print("saved:", OUT, canvas.size)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
