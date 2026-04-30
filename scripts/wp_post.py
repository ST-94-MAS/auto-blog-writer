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
import datetime
import base64
import requests

# === 画像URLの読み込み（オプション） ===
image_url = None
try:
    with open("meta/image_url.txt", encoding="utf-8") as f:
        image_url = f.read().strip()
except FileNotFoundError:
    pass

# === 本日のMarkdownファイル確認 ===
today = datetime.date.today().isoformat()
today_md_files = glob.glob(f"posts/{today}-*.md")

if not today_md_files:
    print(f"❌ Error: 本日のMarkdownファイルが見つかりません（posts/{today}-*.md）", file=sys.stderr)
    sys.exit(1)

md_file = today_md_files[0]  # 本日のファイルを使用

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

# === 画像処理（生成された画像がある場合） ===
featured_media_id = None
if image_url:
    if requests is None:
        print("⚠️ requests がインストールされていないため画像アップロードをスキップします", file=sys.stderr)
    else:
        print("🖼️ WordPressに画像をアップロード中...")
        try:
            wp_url = os.getenv("WP_URL")
            wp_username = os.getenv("WP_USERNAME")
            wp_app_password = os.getenv("WP_APP_PASSWORD")

            if not wp_url or not wp_username or not wp_app_password:
                raise ValueError("WordPress接続情報が不足しています")

            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                wp_upload_url = f"{wp_url}/wp-json/wp/v2/media"
                files = {
                    'file': ('generated-image.png', image_response.content, 'image/png')
                }
                headers = {
                    'Authorization': f'Basic {base64.b64encode(f"{wp_username}:{wp_app_password}".encode()).decode()}'
                }

                upload_response = requests.post(wp_upload_url, files=files, headers=headers)
                if upload_response.status_code == 201:
                    featured_media_id = upload_response.json().get('id')
                    print(f"✅ 画像アップロード完了 (ID: {featured_media_id})")
                else:
                    print(f"⚠️ 画像アップロード失敗: {upload_response.status_code}", file=sys.stderr)
            else:
                print("⚠️ 画像ダウンロード失敗", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 画像処理エラー: {e}", file=sys.stderr)

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

if featured_media_id:
    payload["featured_media"] = featured_media_id

# === JSONファイルとして保存 ===
with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print("✅ payload.json を出力しました")
print("=== payload.json preview ===")
print(json.dumps(payload, ensure_ascii=False, indent=2))
