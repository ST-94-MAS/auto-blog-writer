#!/usr/bin/env python3
"""
scripts/wp_post.py - WordPress 自動投稿スクリプト（payload.json出力のみ、安全性検査付き）
"""

import os
import glob
import markdown
import json
import sys

# 最新 Markdown ファイル検出
md_files = sorted(glob.glob("posts/*.md"))
if not md_files:
    print("❌ Error: No markdown files found in posts/", file=sys.stderr)
    sys.exit(1)
md_file = md_files[-1]

# タイトル生成
basename = os.path.basename(md_file)
title = os.path.splitext(basename)[0]

# Markdown→HTML変換
with open(md_file, encoding="utf-8") as f:
    content_md = f.read()
content_html = markdown.markdown(content_md)

# 危険なタグ・属性の簡易WAFチェック
dangerous_keywords = [
    "<script", "onerror", "onload", "<iframe", "javascript:",
    "base64,", "<img", "<style", "document.", "<svg", "expression(", "eval("
]
detected = [kw for kw in dangerous_keywords if kw in content_html.lower()]
if detected:
    print("❌ 投稿内容に危険なタグまたはコードが含まれています。投稿を中止します。", file=sys.stderr)
    print("検出されたキーワード:", detected, file=sys.stderr)
    sys.exit(1)

# 本文長チェック（5000文字以上は切り捨て）
MAX_LENGTH = 5000
if len(content_html) > MAX_LENGTH:
    print(f"⚠️ 投稿本文が長すぎます（{len(content_html)}文字）。{MAX_LENGTH}文字に切り詰めます。", file=sys.stderr)
    content_html = content_html[:MAX_LENGTH] + "\n<p>...（以下省略）</p>"

# 投稿ペイロード
payload = {
    "title": title,
    "content": content_html,
    "status": "publish"
}

# JSONファイルとして保存
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")

# 内容プレビュー出力
print("=== payload.json preview ===")
print(json.dumps(payload, ensure_ascii=False, indent=2))
