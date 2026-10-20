#!/usr/bin/env python3
"""上传前的包体安全自查（对齐创服平台扫描口径）。

官方 audit_artifact.py 只看结构规范，不看内容风险；平台实扫还会做：
  IMG-QR-URL-001  把包里所有能解码的图片条码解出来，非可信 URL 直接判 CRITICAL
  外联请求         包内出现任何站外域名 / URL 文本
  可疑脚本         eval / Function / 动态插入 script 等

本脚本把这几条做成硬门槛，跑通再上传：
    python3 scripts/audit_minitool.py [path/to/x.zip]

退出码 0 = 可上传；非 0 = 有 CRITICAL 项。
"""
import base64
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ZIP = ROOT / "minitool" / "maimen-zhanbu-minitool.zip"

# XML 命名空间常量：不是网络请求，唯一豁免
NS_OK = ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml")
TEXT_EXT = {".html", ".htm", ".js", ".css", ".json", ".svg", ".txt"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
URL_RE = re.compile(r"https?://[^\s\"'<>()\\]{3,}", re.I)
DOMAIN_RE = re.compile(r"\b([a-z0-9-]+\.)+(?:com|cn|net|org|io|dev|host|app|me|ink|xyz)\b", re.I)


def scan_text(name, text, findings):
    cleaned = text
    for ns in NS_OK:
        cleaned = cleaned.replace(ns, "")
    for m in URL_RE.finditer(cleaned):
        findings.append(("CRITICAL", name, f"站外 URL：{m.group(0)[:70]}"))
    for m in DOMAIN_RE.finditer(cleaned):
        findings.append(("WARN", name, f"域名样式文本：{m.group(0)[:40]}"))
    if re.search(r"data:image/(?:png|jpe?g|webp|gif|bmp);base64,", cleaned, re.I):
        findings.append(("CRITICAL", name, "内联位图 data URI（条码/二维码常见载体）"))
    if re.search(r"\beval\s*\(|new\s+Function\s*\(", cleaned):
        findings.append(("CRITICAL", name, "eval / new Function"))
    if re.search(r"document\.write\s*\(|\.src\s*=\s*[\"']https?:", cleaned):
        findings.append(("WARN", name, "动态写 script/外链 src"))
    if re.search(r"fetch\s*\(|XMLHttpRequest|WebSocket|EventSource", cleaned):
        findings.append(("CRITICAL", name, "联网调用"))


def scan_qr(name, blob, findings):
    """图片一律解码一遍：平台就是靠这一步抓出二维码里的 URL。"""
    try:
        import cv2  # 可选依赖
        import numpy as np
    except ImportError:
        findings.append(("INFO", name, "本机无 opencv，跳过条码解码（包内无图片则无影响）"))
        return
    arr = cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        return
    val, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    if val:
        findings.append(("CRITICAL", name, f"图片条码解出内容：{val[:80]}"))
    else:
        findings.append(("INFO", name, "图片内未解出条码"))


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ZIP
    if not target.is_file():
        sys.exit(f"找不到 {target}")
    findings = []
    with zipfile.ZipFile(target) as z:
        names = z.namelist()
        for n in names:
            blob = z.read(n)
            ext = Path(n).suffix.lower()
            if ext in IMG_EXT:
                findings.append(("CRITICAL", n, "包内携带图片文件（可能被解出 URL）"))
                scan_qr(n, blob, findings)
            elif ext in TEXT_EXT or ext == "":
                try:
                    scan_text(n, blob.decode("utf-8"), findings)
                except UnicodeDecodeError:
                    findings.append(("WARN", n, "非 UTF-8 文本，已跳过"))

    crit = [f for f in findings if f[0] == "CRITICAL"]
    warn = [f for f in findings if f[0] == "WARN"]
    print(f"包：{target.name}  {len(names)} 个文件  {target.stat().st_size} 字节")
    print(f"文件：{', '.join(names)}")
    for lvl, n, msg in findings:
        print(f"  [{lvl}] {n}: {msg}")
    print(f"结论：CRITICAL={len(crit)} WARN={len(warn)}")
    if crit:
        print("不可上传：先清掉上面的 CRITICAL 项")
        sys.exit(1)
    print("可上传")


if __name__ == "__main__":
    main()
