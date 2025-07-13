#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト
"""
import os
import glob
import markdown
import requests
import sys

# 環境変数取得 & トリム
WP_URL          = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME     = os.getenv("WP_USERNAME", "").strip()
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "").strip()

# デバッグ: 投げるエンドポイント & 認証情報
print(f"DEBUG: Posting endpoint -> {WP_URL}/wp-json/wp/v2/posts", file=sys.stderr)
print(f"DEBUG: WP_URL repr={repr(WP_URL)}", file=sys.stderr)
print(f"DEBUG: WP_USERNAME repr={repr(WP_USERNAME)}", file=sys.stderr)
print(f"DEBUG: WP_APP_PASSWORD repr={repr(WP_APP_PASSWORD)} (len={len(WP_APP_PASSWORD)})", file=sys.stderr)

# 必須チェック
if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
    print("Error: WP_URL, WP_USERNAME, or WP_APP_PASSWORD is unset", file=sys.stderr)
    sys.exit(1)

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

# ヘッダーを設定してWAF回避 (curl 互換UA)
headers = {
    "User-Agent": "curl/7.64.1",
    "Content-Type": "application/json; charset=UTF-8"
}

# 投稿ペイロード
payload = {
    "title":   title,
    "content": content_html,
    "status":  "publish"
}

# REST API 呼び出し
resp = requests.post(
    f"{WP_URL}/wp-json/wp/v2/posts",
    auth=(WP_USERNAME, WP_APP_PASSWORD),
    headers=headers,
    json=payload
)
try:
    resp.raise_for_status()
except requests.exceptions.HTTPError as e:
    print(f"❌ Failed to post to WordPress: {e} (status {resp.status_code})", file=sys.stderr)
    print(f"Response body: {resp.text}", file=sys.stderr)
    sys.exit(1)

print("✅ Posted to WordPress:", resp.json().get("link"))

