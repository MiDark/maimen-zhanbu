#!/usr/bin/env python3
"""把 web/index.html 改造成小红书小工具（离线 H5 zip）合规产物。

规范来源：.skill/minitool-zip-builder（SKILL.md + references/*）
三处改造：
  1. 内联 <script> 外置为 app.js（容器 CSP 禁内联脚本）
  2. viewport 补全 maximum-scale/user-scalable（对齐 zip-artifact-spec 模板）
  3. 「存网页/存图」的 a[download] 下载 → xhs.miniTool 存相册（容器禁下载，
     平台能力优先：writeTempFile → saveImageToPhotosAlbum，无容器降级提示）

用法：python3 scripts/build_minitool.py
产物：minitool/dist/{index.html, app.js, mcd_data.js}
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "index.html"
DATA = ROOT / "web" / "mcd_data.js"
OUT = ROOT / "minitool" / "dist"

VIEWPORT_NEW = (
    'content="width=device-width, initial-scale=1.0, '
    'maximum-scale=1.0, user-scalable=no, viewport-fit=cover"'
)

# 容器安全版「导出」块：替换 web 版里 /* ── 导出 ── */ 到 /* ── Toast ── */ 之间内容
EXPORT_BLOCK = '''/* ── 导出 ── */
function safeName(){ return "今日麦占-" + dateStr(NOW); }
/* 小工具容器禁文件下载：走平台能力存相册；无容器能力时提示截图 */
function mtMiniTool(){
  var mt = window.xhs && window.xhs.miniTool;
  return (mt && typeof mt.saveImageToPhotosAlbum === "function") ? mt : null;
}
function savePage(){
  toast("小工具里不用存网页，点「存图」直接进相册");
}
const MAX_SIDE = 16000, MAX_AREA = 4.0e7;
const IMG_CSS = [
  ".topbar,.tabbar,.toast,.sheet,.ritual,.btn,.src,.fold,.vs,.vt{display:none!important}",
  ".view{display:block!important;opacity:1!important;transform:none!important}",
  "#v-gua,#v-store,#v-me{display:none!important}",
  "html,body{background:#F5F0E8!important;padding:0!important;margin:0!important}",
  "main{padding:0 20px!important}"
].join("");
function collectCss(){
  const out = [], sts = document.querySelectorAll("style");
  for (let i = 0; i < sts.length; i++) out.push(sts[i].textContent);
  return out.join("\\n").replace(/&/g, "&amp;").replace(/</g, "&lt;");
}
function saveImage(){
  toast("正在拼图，稍等一下…", 12000);
  setTimeout(function(){
    /* 只导出「今日」页，手机上一屏就看得完 */
    const host = $("v-today").cloneNode(true);
    const drops = host.querySelectorAll(".btn,.src");
    for (let i = 0; i < drops.length; i++) drops[i].parentNode.removeChild(drops[i]);
    host.classList.add("on");

    const w = 420, h = Math.max(900, host.offsetHeight + 40);
    const scale = Math.min(2, MAX_SIDE / Math.max(w, h), Math.sqrt(MAX_AREA / (w * h)));
    const W = Math.round(w * scale), H = Math.round(h * scale);
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H +
      '" viewBox="0 0 ' + w + " " + h + '">' +
      '<foreignObject x="0" y="0" width="' + w + '" height="' + h + '">' +
      '<div xmlns="http://www.w3.org/1999/xhtml" style="width:' + w + 'px;background:#F5F0E8;padding:26px 20px;box-sizing:border-box;font-family:' +
      'Noto Sans SC,PingFang SC,sans-serif">' +
      "<style>" + collectCss() + IMG_CSS + "</style>" + host.innerHTML +
      "</div></foreignObject></svg>";

    const img = new Image();
    img.onload = function(){
      const canvas = document.createElement("canvas");
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#F5F0E8";
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(img, 0, 0, W, H);
      function done(){ toast("存好了，相册里见"); }
      function fail(){ toast("没存上相册，长按页面截图吧"); }
      try {
        const dataUrl = canvas.toDataURL("image/png");
        const mt = mtMiniTool();
        if (mt && typeof mt.writeTempFile === "function"){
          /* 大图先落临时文件，再存相册（平台推荐路径） */
          Promise.resolve(mt.writeTempFile({ data: dataUrl }))
            .then(function(r){
              return Promise.resolve(mt.saveImageToPhotosAlbum({ filePath: r && r.filePath }));
            })
            .then(done, fail);
        } else if (mt) {
          Promise.resolve(mt.saveImageToPhotosAlbum({ filePath: dataUrl })).then(done, fail);
        } else {
          toast("图拼好了，长按或截图保存");
        }
      } catch(e){ toast("图没拼出来，长按页面截图吧"); }
    };
    img.onerror = function(){ toast("图没拼出来，长按页面截图吧"); };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }, 60);
}

/* ── Toast ── */'''

# ES2018+ 语法扫描（直接交付 JS 不得超出 ES2017）
ES2018_PATTERNS = [
    (r"\?\?", "空值合并 ??"),
    (r"\?\.", "可选链 ?."),
    (r"replaceAll\(", "String.replaceAll"),
    (r"\.at\(", "Array/String .at()"),
    (r"Object\.hasOwn", "Object.hasOwn"),
    (r"structuredClone", "structuredClone"),
    (r"\|\|=", "逻辑赋值 ||="),
    (r"&&=", "逻辑赋值 &&="),
    (r"\#\w+\s*=", "class 私有字段"),
]


def build():
    html = SRC.read_text(encoding="utf-8")

    # 1) 抽出内联脚本
    m = re.search(r'<script>\n(.*)\n</script>', html, re.S)
    if not m:
        sys.exit("没找到内联 <script> 块")
    js = m.group(1)

    # 2) 导出块替换为容器安全版
    a = js.find("/* ── 导出 ── */")
    b = js.find("/* ── Toast ── */")
    if a < 0 or b < 0 or b < a:
        sys.exit("没找到导出块标记")
    js = js[:a] + EXPORT_BLOCK + js[b + len("/* ── Toast ── */"):]

    # 3) 内联脚本 → 外置引用
    html = html[:m.start()] + '<script src="./app.js"></script>' + html[m.end():]

    # 4) viewport 升级
    html = re.sub(r'<meta name="viewport" content="[^"]*">',
                  '<meta name="viewport" ' + VIEWPORT_NEW + ">", html)

    # 4.5) 资源引用统一相对路径 ./ 前缀
    html = html.replace('src="mcd_data.js"', 'src="./mcd_data.js"')

    # 5) 写产物
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "app.js").write_text(js, encoding="utf-8")
    shutil.copy2(DATA, OUT / "mcd_data.js")

    # ── 自检 ──
    errors, warns = [], []
    for name, text in (("index.html", html), ("app.js", js)):
        for pat, label in ES2018_PATTERNS:
            if re.search(pat, text):
                errors.append(f"{name}: ES2018+ 语法 {label}")
        if re.search(r'\beval\(|new Function\(', text):
            errors.append(f"{name}: eval/new Function")
    if re.search(r'<script(?![^>]*src=)[^>]*>', html):
        errors.append("index.html: 仍有内联 <script>")
    for pat, label in [("onclick=", "行内事件"), ("javascript:", "javascript: URI"),
                       ("<form", "form 提交"), ("target=", "target 属性"),
                       ("<iframe", "iframe"), ("<object", "object"),
                       ('type="module"', "module 脚本"), ("<base ", "base href")]:
        if pat in html:
            errors.append(f"index.html: {label}")
    if re.search(r'a\.download|\.download\s*=', js):
        errors.append("app.js: a.download 下载残留")
    if re.search(r'fetch\(|XMLHttpRequest|new WebSocket\(|new EventSource\(|new Worker\(', js):
        errors.append("app.js: 联网/Worker 调用残留")
    if re.search(r'window\.open\(|window\.prompt\(|navigator\.geolocation|navigator\.clipboard', js):
        errors.append("app.js: 被禁 API 残留")
    # 外链引用（xmlns 命名空间字符串除外）
    for mm in re.finditer(r'(?:src|href)="(https?://[^"]+)"', html):
        errors.append(f"index.html: 外部引用 {mm.group(1)[:60]}")
    if 'src="./app.js"' not in html or 'src="./mcd_data.js"' not in html:
        errors.append("index.html: 脚本引用缺失")

    sizes = {p.name: p.stat().st_size for p in sorted(OUT.iterdir())}
    print("产物：", OUT)
    for k, v in sizes.items():
        print(f"  {k:<14} {v/1024:.1f} KB")
    print(f"自检：errors={len(errors)}")
    for e in errors:
        print("  ERROR:", e)
    if errors:
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    build()
