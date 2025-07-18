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

# === 最新 Markdown ファイル検出 ===
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("❌ Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# === タイトル生成 ===
basename = os.path.basename(md_file)
raw_title = os.path.splitext(basename)[0]
title = re.sub(r'^\d{8}_?', '', raw_title)
# === Markdown → HTML変換 ===
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# === 危険タグ・属性・コードスニペットの除去関数 ===
def sanitize_html(html: str) -> str:
    # 危険なタグを除去
    html = re.sub(r"<(script|iframe|style|svg).*?>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
    # コードブロックを除去（```〜```）
    html = re.sub(r"```.*?```", "", html, flags=re.DOTALL)
    # 危険な属性（onload, onclick など）
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
aioseo_description = content_md.strip().replace('\n', '').replace('#', '').strip()
aioseo_description = aioseo_description[:120]  # 長すぎると弾かれるため制限

# === 投稿ペイロード生成 ===
payload = {
    "title": title,
    "content": content_html,
    "status": "publish",
    "meta": {
        "aioseo_title": aioseo_title,
        "aioseo_description": aioseo_description
    }
}

# === JSONファイルとして保存 ===
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")

# === 内容プレビュー ===
print("=== payload.json preview ===")
print(json.dumps(payload, ensure_ascii=False, indent=2))
