#!/usr/bin/env python3
import os
import glob
import markdown
import requests
import sys

# 1) 必要な環境変数を取得
WP_URL          = os.getenv("WP_URL")
WP_USERNAME     = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

- name: Show env for debug
  run: |
    echo "WP_URL=$WP_URL"
    echo "WP_USERNAME=$WP_USERNAME"
    echo "WP_APP_PASSWORD=${WP_APP_PASSWORD:0:4}****"

if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
    print("Error: WP_URL, WP_USERNAME, or WP_APP_PASSWORD is unset", file=sys.stderr)
    sys.exit(1)

# 2) 最新の Markdown ファイルを探す
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# 3) タイトルをファイル名から取得
basename = os.path.basename(md_file)
title    = os.path.splitext(basename)[0]

# 4) Markdown → HTML に変換
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# 5) 記事を投稿（タグなし）
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

