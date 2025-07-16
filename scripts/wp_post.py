#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト（payload.json出力、安全対策付き）
"""

import os
import glob
import markdown
import json
import sys
import re

# === 最新 Markdown ファイル検出 ===
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("❌ Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# === タイトル生成 ===
basename = os.path.basename(md_file)
title = os.path.splitext(basename)[0]

# === Markdown → HTML変換 ===
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# === 危険タグ・属性の除去関数 ===
def sanitize_html(html: str) -> str:
    # 危険なタグを除去
    html = re.sub(r"<(script|iframe|style|svg).*?>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
    # 危険な属性を除去（onload, onclickなど）
    html = re.sub(r'on\w+=".*?"', "", html, flags=re.IGNORECASE)
    return html

content_html = sanitize_html(content_html)

# === 本文長制限（5000文字まで）===
MAX_LENGTH = 5000
if len(content_html) > MAX_LENGTH:
    print(f"⚠️ 本文が長すぎます（{len(content_html)}文字）。{MAX_LENGTH}文字に切り詰めます。", file=sys.stderr)
    content_html = content_html[:MAX_LENGTH] + "\n<p>...（以下省略）</p>"

# === 投稿ペイロード生成 ===
payload = {
    "title": title,
    "content": content_html,
    "status": "publish"
}

# === JSONファイルとして保存 ===
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")

# === 内容プレビュー ===
print("=== payload.json preview ===")
print(json.dumps(payload, ensure_ascii=False, indent=2))
