#!/usr/bin/env python3
import os
import glob
import markdown
import requests
import sys

# 必要な環境変数を取得
WP_URL          = os.getenv("WP_URL")
WP_USERNAME     = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
    print("Error: WP_URL, WP_USERNAME, or WP_APP_PASSWORD is unset", file=sys.stderr)
    sys.exit(1)

# 最新の Markdown ファイルを探す
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# ファイル名からタイトルを取得
basename = os.path.basename(md_file)
title    = os.path.splitext(basename)[0]

# Markdown を HTML に変換
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# WordPress に投稿（タグなし）
resp = requests.post(
    f"{WP_URL}/wp-json/wp/v2/posts",
    auth=(WP_USERNAME, WP_APP_PASSWORD),
    json={
        "title":   title,
        "content": content_html,
        "status":  "publish"
    }
)
resp.raise_for_status()

print("✅ Posted to WordPress:", resp.json().get("link"))
