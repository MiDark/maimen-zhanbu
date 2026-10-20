#!/usr/bin/env python3
"""量首屏折线：在给定视口下，今日页的关键块是否都在「底栏之上」的可见区内。

用法：python scripts/measure_fold.py
输出：每个视口一行，列出各块底边与可用高度、以及「抽今日命卡」按钮是否可见。
"""
import json
import os
import re
import subprocess
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web/index.html")

VP = [
    (360, 640, "小屏 Android"),
    (375, 667, "iPhone SE/8"),
    (390, 780, "WorkBuddy 侧栏"),
    (390, 844, "iPhone 14"),
    (430, 932, "iPhone Pro Max"),
]

PROBE = """
<script>
window.addEventListener('load', function(){
  setTimeout(function(){
    function r(sel){ var e=document.querySelector(sel); if(!e) return null;
      var b=e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; }
    var tb=document.querySelector('.tabbar');
    var out={vh: window.innerHeight,
      topbar: r('.topbar'), hero: r('.hero'), score: r('#scoreBig')||r('.score'),
      order: r('.order'), trs: r('#tDo'), btn: r('#btnCard'), src: r('.src'),
      tabbar: tb?Math.round(tb.getBoundingClientRect().top):null,
      doc: Math.round(document.documentElement.scrollHeight)};
    document.body.setAttribute('data-m', JSON.stringify(out));
  }, 300);
});
</script></body>
"""


def main():
    src = open(SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="fold")
    page = src.replace("</body>", PROBE, 1)
    f = os.path.join(tmp, "p.html")
    open(f, "w", encoding="utf-8").write(page)
    import shutil
    shutil.copy(os.path.join(ROOT, "web/mcd_data.js"), os.path.join(tmp, "mcd_data.js"))

    print(f"{'视口':>16}  {'可用高':>6}  {'按钮底':>6}  {'底栏顶':>6}  结论")
    for w, h, name in VP:
        out = os.path.join(tmp, f"s{w}x{h}.png")
        dom = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                              "--hide-scrollbars", "--no-first-run",
                              f"--user-data-dir={tmp}/prof{w}x{h}",
                              f"--window-size={w},{h}", f"--screenshot={out}",
                              "--virtual-time-budget=2500", "--dump-dom", "file://" + f],
                             capture_output=True, text=True).stdout
        m = re.search(r'data-m="([^"]+)"', dom)
        if not m:
            print(f"{name:>16}  测量失败")
            continue
        d = json.loads(m.group(1).replace("&quot;", '"'))
        btn = d.get("btn")
        tab = d.get("tabbar")
        ok = btn and tab and btn[1] <= tab
        print(f"{name:>16}  {d['vh']:>6}  {(btn[1] if btn else -1):>6}  "
              f"{(tab if tab else -1):>6}  {'✅ 可见' if ok else '❌ 被底栏挡住/超出一屏'}")


if __name__ == "__main__":
    main()
