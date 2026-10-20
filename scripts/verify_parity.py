#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三端一致性对拍：Python 引擎 vs 网页版 JS vs 小红书小程序 JS。

做法：不跑浏览器、不依赖 wx 运行时，只把两端 JS 里的「纯计算区」
（GUA64 … calcScore）切出来，在 Node 里对同一批时点求值，逐项比对。

用法：
    python3 scripts/verify_parity.py

退出码 0 表示全部一致；1 表示存在差异（会打印差异明细）。
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fortune_engine as fe  # noqa: E402

NODE = os.environ.get("NODE_BIN") or shutil.which("node") or "node"

# 覆盖 six 个时辰 + 多种外应组合，含闰日与跨年
CASES = [
    (datetime.datetime(2026, 10, 19, 18, 0), "python", 8, 0, False),
    (datetime.datetime(2026, 10, 19, 23, 0), "rust", 20, 0, True),
    (datetime.datetime(2026, 10, 24, 0, 0), "javascript", 0, 0, False),
    (datetime.datetime(2028, 2, 29, 12, 0), "go", 3, 2, False),
    (datetime.datetime(2026, 12, 31, 5, 0), "c++", 40, 6, True),
    (datetime.datetime(2027, 1, 1, 9, 0), "java", 12, 1, False),
]

DRIVER = """
const cases = JSON.parse(process.argv[2]);
const out = cases.map(function (c) {
  const dt = new Date(c[0], c[1] - 1, c[2], c[3], 0, 0, 0);
  const m = meihua(dt);
  const ty = tiyong(m);
  const sub = { lang: c[4], commits: c[5], bugs: c[6], overtime: c[7] };
  return {
    ben: m.benName, hu: m.huName, bian: m.bianName, dong: m.dong,
    bl: m.benLines, hl: m.huLines, xl: m.bianLines,
    up: m.up, down: m.down, huUp: m.huUp, huDown: m.huDown, up2: m.up2, down2: m.down2,
    rel: ty.rel, luck: ty.luck, ti: ty.tiName, yong: ty.yongName,
    order: orderOf((LANG_WUXING[sub.lang] || ["土"])[0], ty.rel, sub, dt),
    card: MING_CARDS[cardIndexOf(sub, dt)][0], score: calcScore(sub, ty)
  };
});
console.log(JSON.stringify(out));
"""


def extract(path: Path, start_pat: str, end_pat: str) -> str:
    """从源文件切出纯计算区（常量表起，渲染/页面逻辑之前）。"""
    src = path.read_text(encoding="utf-8")
    i = src.find(start_pat)
    if i < 0:
        raise SystemExit(f"未找到起点 {start_pat!r} in {path}")
    j = src.find(end_pat, i)
    if j < 0:
        raise SystemExit(f"未找到终点 {end_pat!r} in {path}")
    return src[i:j]


def run_js(engine_js: str, cases) -> list:
    payload = json.dumps([[c[0].year, c[0].month, c[0].day, c[0].hour] + list(c[1:])
                          for c in cases])
    # 计算区里的 require 是给小程序读真实快照的，纯计算用不上，换成空值即可
    engine_js = re.sub(r'const MCD_REAL = require\([^)]*\);', 'const MCD_REAL = null;', engine_js)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(engine_js + "\n" + DRIVER)
        tmp = f.name
    try:
        r = subprocess.run([NODE, tmp, payload], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("Node 执行失败：\n" + r.stderr[-2000:])
        return json.loads(r.stdout)
    finally:
        Path(tmp).unlink(missing_ok=True)


def py_side(case) -> dict:
    dt, lang, commits, bugs, ot = case
    d = fe.calc(lang=lang, commits=commits, bugs=bugs, overtime=ot, now=dt)
    m, ty = d["meihua"], d["tiyong"]
    return {
        "ben": m["ben_name"], "hu": m["hu_name"], "bian": m["bian_name"],
        "dong": m["dong_yao"],
        "bl": m["ben_lines"], "hl": m["hu_lines"], "xl": m["bian_lines"],
        "up": m["up"], "down": m["down"], "huUp": m["hu_up"], "huDown": m["hu_down"],
        "up2": m["up2"], "down2": m["down2"],
        "rel": ty["relation"], "luck": ty["luck"],
        "ti": ty["ti_name"], "yong": ty["yong_name"],
        "order": d["yiji"]["order"],
        "card": d["card"]["name"], "score": d["score"],
    }


def main() -> int:
    engines = {
        "web": extract(ROOT / "web" / "index.html", "const GUA64", "function maiVerdict("),
        "miniprogram": extract(ROOT / "miniprogram" / "pages" / "index" / "index.js",
                               "const GUA64", "Page({"),
    }
    results = {k: run_js(v, CASES) for k, v in engines.items()}

    diffs = 0
    print(f"{'时点':<20}{'本卦':<12}{'互卦':<12}{'变卦':<12}{'动':<3}{'体用':<8}{'分':<4}{'命卡'}")
    print("-" * 92)
    for idx, case in enumerate(CASES):
        dt = case[0]
        base = py_side(case)
        flag = ""
        for name in engines:
            got = results[name][idx]
            for k in base:
                if got.get(k) != base[k]:
                    diffs += 1
                    flag += f"\n  [{name}] {k}: py={base[k]!r} js={got.get(k)!r}"
        print(f"{dt:%Y-%m-%d %H时}  {base['ben']:<10}{base['hu']:<10}"
              f"{base['bian']:<10}{base['dong']:<3}{base['rel']:<8}{base['score']:<4}{base['card']}")
        if flag:
            print(flag)

    print("-" * 92)
    if diffs:
        print(f"FAIL：{diffs} 处不一致")
        return 1
    print(f"ALL MATCH：{len(CASES)} 个时点 × 3 端 × {len(py_side(CASES[0]))} 项，全部一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
