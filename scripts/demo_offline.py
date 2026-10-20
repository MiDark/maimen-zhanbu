#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线演示：把 fortune_engine.py 产出的 JSON 注入命卡模板，生成自包含 HTML。

无需麦当劳 MCP Token，没装 WorkBuddy 也能跑出一张命卡 —— 用于 README 展示与拉 Star。
若本地跑过 scripts/fetch_real.py（生成 assets/mcd_data.js 快照），命卡会自动带上
「去 173 米那家」「领 11.9 元麦辣鸡腿堡」这类真实门店与券，否则退回纯离线版。

用法：
    python scripts/fortune_engine.py --lang python --commits 12 --bugs 1 --out fortune.json
    python scripts/demo_offline.py --data fortune.json --out 麦门命卡.html
    python scripts/demo_offline.py --data fortune.json --real assets/mcd_data.js --out 麦门命卡.html
"""
import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "ming_card.html"
SNAPSHOT = ROOT / "assets" / "mcd_data.js"


def load_real(path):
    """读取真实数据。两种来源都认：
      1) real.json —— 技能运行时由 Agent 依据 MCP 工具结果写下的文件（推荐）
      2) mcd_data.js —— fetch_real.py 生成的 window.MCD_REAL 快照（网页/离线演示用）
    读不到或内容为空则返回 None（命卡退回纯离线）。
    """
    try:
        txt = pathlib.Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None

    real = None
    if txt.startswith("{"):
        try:
            real = json.loads(txt)
        except json.JSONDecodeError:
            return None
    else:
        m = re.search(r"window\.MCD_REAL\s*=\s*(\{[\s\S]*\})\s*;", txt)
        if not m:
            return None
        try:
            real = json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    if not isinstance(real, dict) or real.get("ok") is False:
        return None
    # 手写的 real.json 可能只给一部分字段，缺的不补、有啥用啥
    return real if (real.get("stores") or real.get("coupons") or real.get("campaigns")) else None


def overlay_real(data, real):
    """用真实门店 / 券 / 活动重写宜忌与点单依据（与网页版同一套口径）。"""
    stores = [s for s in (real.get("stores") or []) if isinstance(s.get("distance"), (int, float))]
    st = min(stores, key=lambda s: s["distance"]) if stores else None
    coupons = real.get("coupons") or []
    camps = real.get("campaigns") or []

    wish = ""
    for it in (data.get("yiji", {}).get("yi") or []):
        if "点一份" in it:
            wish = it.replace("点一份", "")
            break
    cp = None
    for key in [k for k in re.split(r"[配和或/、]", wish) if len(k) >= 2]:
        for c in coupons:
            if key and key in (c.get("title") or ""):
                cp = c
                break
        if cp:
            break

    yi, ji = list(data.get("yiji", {}).get("yi") or []), list(data.get("yiji", {}).get("ji") or [])
    if st:
        dist = ("%d 米" % st["distance"]) if st["distance"] < 1000 else ("%.1f 公里" % (st["distance"] / 1000))
        yi.insert(0, "去 %s 那家，走过去不费劲" % dist)
        if st.get("close"):
            ji.append("别等过了 %s 再去" % st["close"])
    if cp:
        yi.insert(0, "领「%s」，今天有便宜占" % cp.get("title", ""))
    elif coupons:
        yi.insert(0, "今天有 %d 张券可领" % len(coupons))
    if camps:
        title = (camps[0].get("title") or "").strip()
        if len(title) > 12:
            title = title[:12] + "…"   # 切一半的名比截断更像 bug，加省略号
        if title:
            yi.append("看一眼「%s」" % title)
    ji.append("空着手出门")

    data.setdefault("yiji", {})
    data["yiji"]["yi"] = yi
    data["yiji"]["ji"] = ji
    data["real"] = {
        "fetched_at": real.get("fetched_at", ""),
        "store": (st or {}).get("name", ""),
        "distance": (st or {}).get("distance"),
        "coupon": (cp or {}).get("title", ""),
    }
    return data


def main():
    ap = argparse.ArgumentParser(description="麦门命卡 离线生成（无需 Token）")
    ap.add_argument("--data", required=True, help="fortune_engine.py 产出的 JSON")
    ap.add_argument("--out", default="麦门命卡.html", help="输出 HTML 路径")
    ap.add_argument("--real", default=None,
                    help="真实数据：real.json（技能运行时由 MCP 结果写入）或 mcd_data.js 快照")
    a = ap.parse_args()

    data = json.load(open(a.data, encoding="utf-8"))
    real = load_real(a.real) if a.real else load_real(SNAPSHOT)
    if real:
        data = overlay_real(data, real)

    tpl = TEMPLATE.read_text(encoding="utf-8")
    out = tpl.replace("__FORTUNE_DATA__", json.dumps(data, ensure_ascii=False))
    pathlib.Path(a.out).write_text(out, encoding="utf-8")
    extra = "，含真实门店与券（%s）" % real.get("fetched_at", "") if real else "，纯离线"
    print("命卡已生成 ->", a.out, "（双击 file:// 直开，零外链%s）" % extra)


if __name__ == "__main__":
    main()
