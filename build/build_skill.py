#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 WorkBuddy 技能包：dist/maimen-zhanbu-skill.zip

结构（顶层目录 = 技能名，与命理全鉴发布包一致）：
    maimen-zhanbu/
      SKILL.md
      mcp-config.example.json
      assets/ming_card.html
      references/mcd_mcp_tools.md
      scripts/*.py

用法：
    python build/build_skill.py            校验 + 打包
    python build/build_skill.py --check    只校验，不出包
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAME = "maimen-zhanbu"
DIST = REPO / "dist"
OUT = DIST / f"{NAME}-skill.zip"

# (仓库内路径, 包内路径)
FILES = [
    ("skill/SKILL.md", "SKILL.md"),
    ("scripts/fortune_engine.py", "scripts/fortune_engine.py"),
    ("scripts/mcp_client.py", "scripts/mcp_client.py"),
    ("scripts/render_page.py", "scripts/render_page.py"),
    ("templates/app.html", "templates/app.html"),
    ("templates/demo_data.js", "templates/demo_data.js"),
    ("references/mcd_mcp_tools.md", "references/mcd_mcp_tools.md"),
]

REQUIRED_META = ("name", "display_name", "description", "version")


def check():
    errs = []
    for src, _ in FILES:
        if not (REPO / src).is_file():
            errs.append(f"缺文件：{src}")

    skill = (REPO / "skill/SKILL.md").read_text(encoding="utf-8")
    lines = skill.splitlines()
    # 分隔符必须是单独一行 ---：曾经出现过 ------（六道杠），YAML 直接失效
    if not lines or lines[0].strip() != "---":
        errs.append("SKILL.md 第一行必须是 ---")
    try:
        end = next(i for i, l in enumerate(lines[1:], start=1) if l.strip() == "---")
    except StopIteration:
        errs.append("SKILL.md 的 frontmatter 没有闭合的 ---")
        end = 0
    if end:
        head = "\n".join(lines[1:end])
        for key in REQUIRED_META:
            if not re.search(rf"^{key}\s*:\s*\S", head, re.M):
                errs.append(f"frontmatter 缺 {key}")
        m = re.search(r"^name\s*:\s*(\S+)", head, re.M)
        if m and m.group(1) != NAME:
            errs.append(f"frontmatter name={m.group(1)}，与包名 {NAME} 不一致")
        v = re.search(r"^version\s*:\s*(\S+)", head, re.M)
        if v and not re.match(r"^\d+\.\d+\.\d+$", v.group(1)):
            errs.append(f"version 不是 x.y.z：{v.group(1)}")

    # 包内脚本用 parent.parent 找 assets/，确认这层关系没变
    demo = (REPO / "scripts/demo_offline.py").read_text(encoding="utf-8")
    if "parent.parent" not in demo:
        errs.append("demo_offline.py 的资源路径不再是 parent.parent，包结构需同步调整")

    # templates/app.html 是 web/index.html 的副本：改了线上页面忘了同步，这里要拦
    web = (REPO / "web/index.html").read_text(encoding="utf-8")
    tpl = (REPO / "templates/app.html").read_text(encoding="utf-8")
    if web != tpl:
        errs.append("templates/app.html 与 web/index.html 不一致：先 cp web/index.html templates/app.html")

    # 包里不能有真实凭证
    for src, _ in FILES:
        txt = (REPO / src).read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\b[0-9a-fA-F]{32}\b", txt) or re.search(r"Bearer\s+[A-Za-z0-9]{12,}", txt):
            errs.append(f"疑似真实凭证：{src}")

    return errs


def build():
    # 沙箱里 mkdir(exist_ok=True) 遇到已存在的目录也会抛 PermissionError，先判存在
    if not DIST.is_dir():
        DIST.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in FILES:
            z.write(REPO / src, f"{NAME}/{dst}")
    return OUT


INSTALL = Path.home() / ".workbuddy" / "skills" / NAME


def install():
    """装进本地技能目录，供 WorkBuddy 里直接对话测试（先清空，避免旧文件残留）"""
    if INSTALL.is_dir():
        shutil.rmtree(INSTALL, ignore_errors=True)
    for src, dst in FILES:
        target = INSTALL / dst
        if not target.parent.is_dir():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / src).read_bytes())
    return INSTALL


def main():
    ap = argparse.ArgumentParser(description="打包 WorkBuddy 技能包")
    ap.add_argument("--check", action="store_true", help="只校验，不出包")
    ap.add_argument("--install", action="store_true", help="同时装到 ~/.workbuddy/skills/")
    a = ap.parse_args()

    errs = check()
    if errs:
        print("✗ 校验未通过：")
        for e in errs:
            print("  -", e)
        return 1
    print("✓ 校验通过（%d 个文件）" % len(FILES))
    if a.install:
        dst = install()
        print(f"✓ 已安装到 {dst}")
    if a.check:
        return 0

    out = build()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    size = out.stat().st_size / 1024
    print(f"✓ 已打包 {out.relative_to(REPO)}（{len(names)} 个条目，{size:.0f} KB）")
    for n in names:
        print("   ", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
