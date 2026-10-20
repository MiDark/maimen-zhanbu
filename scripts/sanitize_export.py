#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脱敏导出工具：从对话/文本导出 Markdown 分享或 workbuddy.md 之前，自动 redact 敏感凭证。

用法：
    # 管道
    cat 对话原文.txt | python scripts/sanitize_export.py --out workbuddy.md
    # 或直接读文件
    python scripts/sanitize_export.py --infile 原始对话.md --out workbuddy.md

redact 项：32 位十六进制 Token、Bearer 令牌、手机号、邮箱。
规则：凡对外发布的参赛材料，导出前必须过本工具，真实凭证永不入仓。
"""

import re
import sys
import argparse

TOKEN_RE = re.compile(r"\b[0-9a-fA-F]{32}\b")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")


def redact(text: str) -> str:
    text = BEARER_RE.sub("Bearer 〈已脱敏〉", text)
    text = TOKEN_RE.sub("〈MCP_TOKEN_已脱敏_32位〉", text)
    text = PHONE_RE.sub("〈手机号_已脱敏〉", text)
    text = EMAIL_RE.sub("〈邮箱_已脱敏〉", text)
    return text


def main():
    ap = argparse.ArgumentParser(description="脱敏导出：redact Token/手机/邮箱后输出 Markdown")
    ap.add_argument("--infile", default="-", help="输入文件，- 表示 stdin")
    ap.add_argument("--out", default="-", help="输出文件，- 表示 stdout")
    a = ap.parse_args()

    if a.infile == "-":
        src = sys.stdin.read()
    else:
        with open(a.infile, encoding="utf-8") as f:
            src = f.read()

    out = redact(src)

    if a.out == "-":
        print(out)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
        print("脱敏导出 ->", a.out)


if __name__ == "__main__":
    main()
