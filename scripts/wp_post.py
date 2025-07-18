#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト（payload.json出力、安全対策＋SEO対応）
"""

import os
import glob
import markdown
import json
import sys
import re

# === 投稿タイトルの読み込み ===
try:
    with open("meta/title.txt", encoding="utf-8") as f:
        title = f.read().strip()
except FileNotFoundError:
    print("❌ Error: meta/title.txt が見つかりません", file=sys.stderr)
    sys.exit(1)

# === 最新 Markdown ファイル検出 ===
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("❌ Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# === Markdown 読込・整形 ===
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()

# Markdown内にある不要な`#`を削除（description用）
clean_md = re.sub(r'#\s*', '', content_md).replace('\n', '').strip()

# === HTML変換（先に画像タグ修正も） ===
def preprocess_md(md: str) -> str:
    # 画像タグの src="", alt="" が欠けるケースに備えて代替処理
    # md = re.sub(r'!\[\]\((.*?)\)', r'<img src="\1" alt="画像" />', md)
    return md

html_source = preprocess_md(content_md)
content_html = markdown.markdown(html_source)

# === 危険タグ・属性・コードスニペットの除去関数 ===
def sanitize_html(html: str) -> str:
    html = re.sub(r"<(script|iframe|style|svg).*?>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"```.*?```", "", html, flags=re.DOTALL)
    html = re.sub(r'on\w+=".*?"', "", html, flags=re.IGNORECASE)
    return html

content_html = sanitize_html(content_html)

# === 本文長制限（9000文字まで）===
MAX_LENGTH = 9000
if len(content_html) > MAX_LENGTH:
    print(f"⚠️ 本文が長すぎます（{len(content_html)}文字）。{MAX_LENGTH}文字に切り詰めます。", file=sys.stderr)
    content_html = content_html[:MAX_LENGTH] + "\n<p>...（以下省略）</p>"

# === SEO用メタ情報 ===
aioseo_title = f"{title} | OtomosaBlog"
aioseo_description = clean_md[:120]

# === 投稿ペイロード生成 ===
payload = {
    "title": title,
    "content": content_html,
    "status": "publish",
    "meta": {
        "_aioseo_title": aioseo_title,
        "_aioseo_description": aioseo_description
    }
}

# === JSONファイルとして保存 ===
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")
print("=== payload.json preview ===")
print(json.dumps(payload, ensure_ascii=False, indent=2))
