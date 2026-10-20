#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成技能头像：512×512 PNG，麦当劳经典红黄配色。

纯本地绘制，不调用任何外部接口。
    python3 build/make_avatar.py          # 主方案：红底黄字 → assets/avatar-512.png
    python3 build/make_avatar.py --alt    # 备选：黄底红字 → assets/avatar-512-alt.png
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 512

MCD_RED = (218, 41, 28)        # 麦当劳红
MCD_RED_DEEP = (176, 30, 20)
MCD_YELLOW = (255, 199, 44)    # 金拱门黄
MCD_YELLOW_DEEP = (232, 172, 20)

FONTS = [
    ("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", 6),   # 明朝：粗细对比强，最像印面
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
]


def load_font(px):
    for path, idx in FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, px, index=idx)
            except OSError:
                continue
    raise SystemExit("没找到可用的中文字体")


def field(base, deep, softness=26):
    """底色：整块铺满，只叠极轻的噪点，避免大色块发闷、也压掉渐变带"""
    img = Image.new("RGB", (SIZE, SIZE), base)
    noise = Image.effect_noise((SIZE, SIZE), softness).convert("L").filter(ImageFilter.GaussianBlur(1.0))
    dark = Image.new("RGB", (SIZE, SIZE), deep)
    return Image.composite(dark, img, noise.point(lambda v: int(max(0, v - 128) * 0.35)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", action="store_true", help="黄底红字版本")
    a = ap.parse_args()

    if a.alt:
        bg, bg_deep = MCD_YELLOW, MCD_YELLOW_DEEP
        ink = MCD_RED
        out_name = "avatar-512-alt.png"
    else:
        bg, bg_deep = MCD_RED, MCD_RED_DEEP
        ink = MCD_YELLOW
        out_name = "avatar-512.png"

    img = field(bg, bg_deep).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 内框：与字同色，细、留白足；缩到 48px 仍能看出「有边框」
    inset = 34
    d.rounded_rectangle([inset, inset, SIZE - inset, SIZE - inset],
                        radius=26, outline=ink + (235,), width=5)

    # 主字：占
    font = load_font(292)
    text = "占"
    bb = d.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx = (SIZE - tw) / 2 - bb[0] + 6
    ty = (SIZE - th) / 2 - bb[1] + 4

    # 先压一层极淡的暗影，模拟油墨压进纸面；再上主色
    shade = tuple(max(0, c - 46) for c in ink)
    d.text((tx + 2, ty + 3), text, font=font, fill=shade + (110,))
    d.text((tx, ty), text, font=font, fill=ink + (255,))

    dst = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", out_name)
    out = img.convert("RGB")
    out.save(dst, "PNG", optimize=True)
    print(f"saved {dst}  {out.size[0]}×{out.size[1]}  {os.path.getsize(dst)/1024:.1f} KB")


if __name__ == "__main__":
    main()
