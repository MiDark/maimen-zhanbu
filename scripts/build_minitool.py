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
import base64
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "index.html"
DATA = ROOT / "web" / "mcd_data.js"
OUT = ROOT / "minitool" / "dist"
QR_PNG = ROOT / "minitool" / "assets" / "qr-web.png"

# 网页版地址（小工具唯一能「把人送出去」的落点：扫码 / 存图识别）
WEB_URL = "https://midark.github.io/maimen-zhanbu/"

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

# 小工具版「去网页版」区块：容器禁联网 / 禁跳外链 / 禁剪贴板，
# 所以只有两条路 —— ① 扫二维码 ② 存图后用微信「扫一扫→相册」识别；
# 另外把地址做成可选中文本，并可选唤起评论区把地址带走（9.49+）。
MINITOOL_LIVE_BLOCK = '''<!-- 小工具版：容器禁联网/禁外链/禁剪贴板 → 用二维码把人送到网页版 -->
    <style>
      .qrimg{display:block;width:186px;height:186px;margin:14px auto 8px;
        border:1px solid var(--line);background:#FFFDF8;padding:6px;}
      .qrtip{text-align:center;font-size:12.5px;color:var(--ink-300);line-height:1.75;margin-bottom:6px;}
      .qrtip b{color:var(--ink-700);}
      .urlbox{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:12.5px;line-height:1.65;
        color:var(--cinnabar-dark);background:rgba(181,74,58,.06);border:1px solid var(--line);
        padding:10px 12px;margin-top:12px;word-break:break-all;
        -webkit-user-select:text;user-select:text;}
    </style>
    <div class="block" id="webBlock">
      <div class="bt">查实时 · 去网页版</div>
      <div class="about">
        小工具是<b>离线包</b>：容器不联网，所以这里的门店 / 券 / 活动只能是<b>打包那一刻的快照</b>。
        <br><br>
        要看<b>此刻</b>的门店和券，去<b>网页版</b>——同一套卦，数据是活的，还能填自己的 Token 看积分。
      </div>
      <img class="qrimg" id="qrImg" src="__QR_DATA_URI__" alt="麦门占卜网页版二维码">
      <div class="qrtip">用<b>另一台手机</b>扫它；或点下面存图，<br>再用微信「扫一扫 → 相册」识别这张图</div>
      <button class="btn" id="btnQrSave">存 二 维 码 到 相 册</button>
      <button class="btn ghost" id="btnComment">把 地 址 带 到 评 论 区</button>
      <div class="urlbox" id="webUrl">__WEB_URL__</div>
      <p class="note" id="webHint">长按上面这行可以选中地址（容器没有一键复制）。</p>
    </div>'''


def qr_data_uri() -> str:
    """把二维码 PNG 内联成 data URI —— 容器里 data: 图片可用，也方便直接喂给存相册 API。"""
    if not QR_PNG.is_file():
        sys.exit("缺 minitool/assets/qr-web.png，先跑 scripts/make_qr.py")
    return "data:image/png;base64," + base64.b64encode(QR_PNG.read_bytes()).decode("ascii")

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
    #      mcd_live.js 不引入，整块 UI 换成「扫码去网页版」
    html = re.sub(r'<script src="\.?/?mcd_live\.js"></script>\s*', "", html)
    block = (MINITOOL_LIVE_BLOCK
             .replace("__QR_DATA_URI__", qr_data_uri())
             .replace("__WEB_URL__", WEB_URL))
    html = re.sub(r"<!-- LIVE-BLOCK-START.*?<!-- LIVE-BLOCK-END -->",
                  lambda _m: block, html, flags=re.S)
    if "liveBlock" in html or "mcd_live.js" in html or "__QR_DATA_URI__" in html:
        sys.exit("实时接入块没替换干净")

    # 4.65) 今日页给一个直达入口：小工具里没有底部强引导，靠这一行把人带到「我的」页
    src_line = '<p class="src" id="srcLine">麦当劳数据</p>'
    if src_line not in html:
        sys.exit("没找到今日页的 srcLine")
    html = html.replace(
        src_line,
        src_line + '\n    <button class="btn ghost" id="btnGoWeb">去 网 页 版 看 实 时</button>',
    )

    # 4.6) 外链降级：容器禁打开外链，Star 链接去掉 href/target，点击由 JS 提示项目名
    html = re.sub(
        r'<a (id="starLink[^"]*") href="https://[^"]*" target="_blank" rel="noopener">',
        r'<a \1 href="#">',
        html,
    )

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
    # 去网页版的三件套：二维码 data URI、存图按钮、今日页入口
    for need in ('data:image/png;base64,', 'id="btnQrSave"', 'id="btnGoWeb"'):
        if need not in html:
            errors.append(f"index.html: 缺「去网页版」要素 {need}")

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
