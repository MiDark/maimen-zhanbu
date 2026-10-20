#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓一次麦当劳只读真实数据，生成网页可用的快照脚本。

网页是静态的（`file://` 双击直开、零外链），不能自己发请求，也不能把 Token 写进页面。
所以由本脚本在**本地**抓一次，落成 `window.MCD_REAL = {...}` 给页面引用：

    MCD_MCP_TOKEN=xxx python3 scripts/fetch_real.py --city 成都 --keyword 春熙路

产物：
  web/mcd_data.js        网页端读取（<script src="mcd_data.js">，file:// 同目录可加载）
  assets/mcd_data.js     命卡模板读取（同一份）

页面顶部会显示抓取时间，明确它是快照而非「实时」。
未配置 Token 时不写文件，页面自动显示「尚未接入」并把入口指向门店页说明。
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcp_client as mc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description="抓取麦当劳 MCP 只读数据，生成网页快照")
    ap.add_argument("--city", default="成都", help="城市名（与 keyword 至少给一个）")
    ap.add_argument("--keyword", default="春熙路", help="关键词/地标")
    ap.add_argument("--out", default=None, help="额外输出 JSON 路径（调试用）")
    ap.add_argument("--with-account", action="store_true",
                    help="连个人积分一起写入（默认三项全脱敏为 null，便于安全提交）")
    a = ap.parse_args()

    if not os.environ.get("MCD_MCP_TOKEN"):
        print("✗ 未设置 MCD_MCP_TOKEN，跳过。页面会显示「尚未接入」。")
        return 1

    data = mc.consult(city=a.city, keyword=a.keyword)
    if not data.get("ok"):
        print("✗ 未取到真实数据：", data.get("reason"))
        return 2

    pts = data.get("points") or None
    if pts and not a.with_account:
        # 默认全脱敏：积分属于个人账户数据，不写进可提交的快照
        pts = {"available": None, "accumulative": None, "expiring": None}

    payload = {
        "ok": True,
        "city": a.city,
        "keyword": a.keyword,
        "fetched_at": data.get("fetched_at", ""),
        "now": data.get("now"),
        "points": pts,
        "stores": data.get("stores", []),
        "coupons": data.get("coupons", []),
        "campaigns": data.get("campaigns", []),
        "lottery": data.get("lottery"),
    }
    js = ("/* 麦当劳开放平台只读快照 —— 由 scripts/fetch_real.py 生成，"
          "含抓取时间，请勿当作实时数据 */\n"
          "window.MCD_REAL = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n")

    for rel in ("web/mcd_data.js", "assets/mcd_data.js"):
        f = ROOT / rel
        if not f.parent.is_dir():
            continue          # 技能包内没有 web/，跳过而不是报错
        f.write_text(js, encoding="utf-8")
        print("written ->", rel)

    # 小程序 / 小工具离线包用的 CommonJS 版本（同一份数据，格式不同）
    mp = ROOT / "miniprogram/data/mcd_real.js"
    if mp.parent.is_dir():
        mp.write_text(
            "/* 麦当劳开放平台只读快照 —— 由 scripts/fetch_real.py 生成，含抓取时间，"
            "请勿当作实时数据；账户数据已脱敏 */\n"
            "module.exports = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n",
            encoding="utf-8",
        )
        print("written -> miniprogram/data/mcd_real.js")

    if a.out:
        Path(a.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✓ 门店 {len(payload['stores'])} / 券 {len(payload['coupons'])} / "
          f"活动 {len(payload['campaigns'])} / 抓取于 {payload['fetched_at']}")
    if not a.with_account:
        print("  积分已脱敏（页面显示 —）。要写真实积分加 --with-account，"
              "但别把结果提交进仓库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
