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

# XML 命名空间常量：SVG 序列化必须要，且不是网络请求，安全扫描里唯一的豁免项
W3C_NS = ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml")

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

# 小工具版：容器禁联网 / 禁跳外链 / 禁剪贴板，且平台安全扫描会把**图片里的二维码**
# 解码出来判风险（IMG-QR-URL-001），所以包里既不能有站外 URL 文本，也不能有二维码图。
# 这里只讲清楚「为什么这里是快照、实时数据去哪看」，不给地址、不放码。
MINITOOL_LIVE_BLOCK = '''<!-- 小工具版：离线快照说明（包内不含任何站外 URL / 二维码） -->
    <style>
      .howto{font-size:13px;line-height:2;color:var(--ink-700);margin:10px 0 2px}
      .howto i{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;
        font-style:normal;font-size:11.5px;border-radius:50%;margin-right:8px;
        background:rgba(181,74,58,.10);color:var(--cinnabar-dark);font-weight:700}
      .howto b{color:var(--ink-900)}
    </style>
    <div class="block" id="webBlock">
      <div class="bt">实时数据 · 怎么看</div>
      <div class="about">
        小工具是<b>离线包</b>：容器不联网，所以这里的门店 / 券 / 活动是<b>打包那一刻的快照</b>，
        页脚写着抓取时间（服务端每 3 小时刷一次）。
        <br><br>
        要查<b>此刻</b>的店和券、以及自己的积分，用<b>网页版</b>——同一套卦，数据是活的。
      </div>
      <div class="howto">
        <div><i>1</i>用手机或电脑的浏览器，打开 <b>GitHub</b></div>
        <div><i>2</i>搜项目名 <b>maimen-zhanbu</b>（开源的那个）</div>
        <div><i>3</i>仓库首页第一行就是<b>在线体验</b>入口</div>
      </div>
      <p class="note" id="webHint">
        这一版是离线包，数据以页脚的抓取时间为准；要活的数据就走上面那条路。
      </p>
    </div>'''

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

    # 2.5) 实时取数整段删除：容器禁网，进度里也不该出现 fetch 字样
    if "LIVE-JS-START" not in js or "LIVE-JS-END" not in js:
        sys.exit("没找到实时取数代码标记（LIVE-JS-START/END）")
    js = re.sub(r"/\* LIVE-JS-START.*?/\* LIVE-JS-END \*/\n*", "", js, flags=re.S)
    if "fetch(" in js or "MCD_LIVE" in js:
        sys.exit("实时取数代码没删干净")

    # 3) 内联脚本 → 外置引用
    html = html[:m.start()] + '<script src="./app.js"></script>' + html[m.end():]

    # 4) viewport 升级
    html = re.sub(r'<meta name="viewport" content="[^"]*">',
                  '<meta name="viewport" ' + VIEWPORT_NEW + ">", html)

    # 4.5) 资源引用统一相对路径 ./ 前缀
    html = html.replace('src="mcd_data.js"', 'src="./mcd_data.js"')

    # 4.6) 实时接入降级：容器禁联网、禁跳外链、禁剪贴板，
    #      且平台安全扫描会解码包内图片里的二维码（IMG-QR-URL-001），
    #      mcd_live.js 不引入，整块 UI 换成「离线快照 + 按项目名自己去搜」
    html = re.sub(r'<script src="\.?/?mcd_live\.js"></script>\s*', "", html)
    html = re.sub(r"<!-- LIVE-BLOCK-START.*?<!-- LIVE-BLOCK-END -->",
                  lambda _m: MINITOOL_LIVE_BLOCK, html, flags=re.S)
    if "liveBlock" in html or "mcd_live.js" in html:
        sys.exit("实时接入块没替换干净")

    # 4.65) 今日页给一个入口：小工具里没有底部强引导，靠这一行把人带到说明区
    src_line = '<p class="src" id="srcLine">麦当劳数据</p>'
    if src_line not in html:
        sys.exit("没找到今日页的 srcLine")
    html = html.replace(
        src_line,
        src_line + '\n    <button class="btn ghost" id="btnGoWeb">实 时 数 据 怎 么 看</button>',
    )

    # 4.6) 外链降级：容器禁打开外链，Star 链接去掉 href/target，点击由 JS 提示项目名
    html = re.sub(
        r'<a (id="starLink[^"]*") href="https://[^"]*" target="_blank" rel="noopener">',
        r'<a \1 href="#">',
        html,
    )
    # 4.62) 连「github.com/…」这种可见域名文本也去掉：包体扫描对域名很敏感，
    #       统一换成「搜项目名」的说法
    html = html.replace(">github.com/MiDark/maimen-zhanbu<", ">GitHub 搜 maimen-zhanbu<")
    html = html.replace(">MiDark/maimen-zhanbu<", ">GitHub 搜 maimen-zhanbu<")

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

    # ── 包体安全扫描对拍（IMG-QR-URL-001 之类的硬门槛）──
    # 1) 任何站外 URL 文本都不许出现，唯一豁免是 XML 命名空间常量
    for name, text in (("index.html", html), ("app.js", js)):
        cleaned = text
        for ns in W3C_NS:
            cleaned = cleaned.replace(ns, "")
        for mm in re.finditer(r"https?://[^\s\"'<>()\\]{3,}", cleaned):
            errors.append(f"{name}: 包内含站外 URL {mm.group(0)[:50]}")
        if "midark.github.io" in cleaned:
            errors.append(f"{name}: 包内含 GitHub Pages 域名")
        if "github.com/" in cleaned:
            errors.append(f"{name}: 包内含 github.com 路径文本")
    # 2) 不许内联位图（二维码就是靠这个混进来的）
    for name, text in (("index.html", html), ("app.js", js)):
        if re.search(r"data:image/(?:png|jpe?g|webp|gif);base64,", text):
            errors.append(f"{name}: 内联位图 data URI（疑似二维码）")
        if re.search(r"<img[^>]+src=", text):
            errors.append(f"{name}: 含 <img> 图片元素")
    # 3) 结构要素：说明区 + 今日页入口，且没有二维码相关残留
    for need in ('id="webBlock"', 'id="btnGoWeb"'):
        if need not in html:
            errors.append(f"index.html: 缺要素 {need}")
    for bad in ("qrImg", "btnQrSave", "btnComment", "webUrl", "interactionOpenApi"):
        if bad in html or bad in js:
            errors.append(f"index.html: 二维码/评论残留 {bad}")

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
