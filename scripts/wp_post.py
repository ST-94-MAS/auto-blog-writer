#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト
"""
import os
import glob
import markdown
import requests
import sys

# 必要な環境変数を取得し、余計な空白を除去
WP_URL          = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME     = os.getenv("WP_USERNAME", "").strip()
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "").strip()

# デバッグ: 環境変数の内容を確認
print(f"DEBUG: Posting endpoint -> {WP_URL}/wp-json/wp/v2/posts", file=sys.stderr)
print(f"DEBUG: WP_URL repr={repr(WP_URL)}", file=sys.stderr)
print(f"DEBUG: WP_USERNAME repr={repr(WP_USERNAME)}", file=sys.stderr)
print(f"DEBUG: WP_APP_PASSWORD repr={repr(WP_APP_PASSWORD)} (len={len(WP_APP_PASSWORD)})", file=sys.stderr)

# 必要な環境変数チェック
if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
    print("Error: WP_URL, WP_USERNAME, or WP_APP_PASSWORD is unset", file=sys.stderr)
    sys.exit(1)

# 最新の Markdown ファイルを探す
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# Markdown ファイル名から投稿タイトルを生成
basename = os.path.basename(md_file)
title    = os.path.splitext(basename)[0]

# Markdown を HTML に変換
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# 投稿用ペイロード
payload = {
    "title":   title,
    "content": content_html,
    "status":  "publish"
}

# WordPress REST API へ投稿
resp = requests.post(
    f"{WP_URL}/wp-json/wp/v2/posts",
    auth=(WP_USERNAME, WP_APP_PASSWORD),
    json=payload
)
try:
    resp.raise_for_status()
except requests.exceptions.HTTPError as e:
    print(f"❌ Failed to post to WordPress: {e} (status {resp.status_code})", file=sys.stderr)
    print(f"Response body: {resp.text}", file=sys.stderr)
    sys.exit(1)

print("✅ Posted to WordPress:", resp.json().get("link"))

