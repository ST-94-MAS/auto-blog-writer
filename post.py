#!/usr/bin/env python3
# post.py

import os
import sys
import datetime
import csv
from dotenv import load_dotenv
import openai
import random
import re
from openai.error import RateLimitError, OpenAIError

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: 環境変数 OPENAI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key

    try:
        with open("keywords.csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            keywords = [row[0].strip() for row in reader if row]
    except FileNotFoundError:
        print("Error: keywords.csv が見つかりません", file=sys.stderr)
        sys.exit(1)
    if not keywords:
        print("Error: keywords.csv にキーワードがありません", file=sys.stderr)
        sys.exit(1)

    selected_keywords = random.sample(keywords, k=random.randint(1, 4))
    keyword = ", ".join(selected_keywords)
    keyword_for_img = selected_keywords[0]

    prompt = f"""
あなたはプロの日本語技術ブログライターです。
以下の条件に基づき、HTML形式のWordPress用記事を書いてください。

【キーワード】{keyword}

【条件】
- <html> や <head> は出力しないでください（<body>内のコンテンツのみ）
- WordPress の HTML編集モードに直接貼り付けられる形式で書いてください
- 以下のHTML構造を守る：
  ・<h1>タイトル（キーワード含む）</h1>
  ・導入文（<p>タグ、キーワード自然に1〜2回使用）
  ・本文は<h2><h3>構成＋PREP法（Point→Reason→Example→Point再提示）
  ・<ul> <ol> <table>など視覚的表現を活用
  ・画像は最低1枚必ず含めてください。
    <img src="https://source.unsplash.com/800x600/?{keyword_for_img}" alt="{keyword_for_img}のイメージ" />
    ※画像URLは実在するURL（Unsplash API）で、空のimgタグやダミーURLは使わないでください
  ・コード例（AWS CDK / GitHub Actions など）も活用可能
  ・最後に<h2>まとめ</h2>で要点を整理してください
"""

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful technical writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7,
        )
    except RateLimitError:
        print("Error: レートリミットを超えました。プランと請求情報を確認してください。", file=sys.stderr)
        sys.exit(1)
    except OpenAIError as e:
        print(f"Error: OpenAI API リクエストに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    content = resp.choices[0].message.content.strip()

    title = "Untitled"
    match_md = re.search(r'^# (.+)', content, re.MULTILINE)
    match_html = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE) or \
                 re.search(r'<h1>(.+?)</h1>', content, re.IGNORECASE)

    if match_md:
        title = match_md.group(1).strip()
    elif match_html:
        title = match_html.group(1).strip()

    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    safe_title = safe_title[:50]

    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{today}-{safe_title}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Markdown saved: {filename}")
    print(f"📌 タイトル: {title}")

    # タイトル保存（SEOにも利用）
    os.makedirs("meta", exist_ok=True)
    with open("meta/title.txt", "w", encoding="utf-8") as f:
        f.write(title)

if __name__ == "__main__":
    main()
