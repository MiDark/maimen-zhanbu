#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「单页应用」打成一张自包含网页：真实数据直接焊进页面，双击即开。

产出与网页版完全同一套版式（今日 / 卦象 / 门店 / 我的 四页），不是另一张卡片。

用法：
    python3 scripts/render_page.py --out 麦门占卜-今日.html
    python3 scripts/render_page.py --real real.json --out 麦门占卜-今日.html
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "app.html"
SNAPSHOT = ROOT / "templates" / "demo_data.js"
TAG = '<script src="mcd_data.js"></script>'


def load_real(path):
    """real.json（运行时）或 *.js（window.MCD_REAL 快照）都认；读不到返回 None。"""
    if not path:
        return None
    p = pathlib.Path(path)
    try:
        txt = p.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if txt.startswith("{"):
        try:
            data = json.loads(txt)
        except json.JSONDecodeError:
            return None
    else:
        m = re.search(r"window\.MCD_REAL\s*=\s*(\{[\s\S]*\})\s*;", txt)
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict) or data.get("ok") is False:
        return None
    return data if (data.get("stores") or data.get("coupons") or data.get("campaigns")) else None


def main():
    ap = argparse.ArgumentParser(description="生成自包含单页应用（与网页版同一套版式）")
    ap.add_argument("--real", default=None, help="real.json（本次查到的真实数据）")
    ap.add_argument("--out", default="麦门占卜-今日.html", help="输出 HTML 路径")
    a = ap.parse_args()

    tpl = TEMPLATE.read_text(encoding="utf-8")
    if TAG not in tpl:
        raise SystemExit("模板里没找到数据占位，无法内联")

    real = load_real(a.real)
    if real is None and SNAPSHOT.exists():
        real = load_real(SNAPSHOT)
        if real:
            real["demo"] = True          # 页面会把它标成「示例数据」，别让人当成实时
    payload = json.dumps(real, ensure_ascii=False) if real else "null"
    inline = "<script>window.MCD_REAL = %s;</script>" % payload
    out_html = tpl.replace(TAG, inline, 1)

    # 离线自包含：不依赖任何外部文件
    dst = pathlib.Path(a.out)
    dst.write_text(out_html, encoding="utf-8")

    if real:
        n_store = len(real.get("stores") or [])
        n_coupon = len(real.get("coupons") or [])
        print(f"已生成 {dst}（{dst.stat().st_size/1024:.0f} KB）"
              f"，含真实数据：{real.get('city','')} 门店 {n_store} / 券 {n_coupon}"
              f" / 抓取于 {real.get('fetched_at','')}")
    else:
        print(f"已生成 {dst}（{dst.stat().st_size/1024:.0f} KB），无真实数据，按离线版出")


if __name__ == "__main__":
    main()
