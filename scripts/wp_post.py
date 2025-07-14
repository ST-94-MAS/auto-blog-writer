#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト（payload.json出力のみ）
"""
import os
import glob
import markdown
import json
import sys

# 最新 Markdown ファイル検出
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# タイトル生成
basename = os.path.basename(md_file)
title    = os.path.splitext(basename)[0]

# Markdown→HTML
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# 投稿ペイロード
payload = {
    "title":   title,
    "content": content_html,
    "status":  "publish"
}

# JSONファイルとして保存
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")

