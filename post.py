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
    # .env ファイルから環境変数を読み込む
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: 環境変数 OPENAI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key

    # キーワード CSV を読み込んでリスト化
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

    # ランダムに 1〜4 個のキーワードを選ぶ
    selected_keywords = random.sample(keywords, k=random.randint(1, 4))
    keyword = ", ".join(selected_keywords)

    # プロンプトを組み立て（<html>全体ではなく本文構造のみ生成するよう指示）
    prompt = f"""
あなたはプロの技術ブログライターです。
以下のキーワードに沿って、WordPress用の記事を日本語で執筆してください。

・キーワード: {keyword}
・WordPressのHTML編集モードに貼れる形式で、
  「<body>内のコンテンツ部分（h1/h2/p/img/tableなど）」のみを生成してください。
・<html> や <head> などの全体構造タグは出力しないでください。

構成:
① タイトル（h1）検索キーワードを含める
② 導入文（リード文）キーワードを自然に1～2回含める
③ 見出し構成（h2 > h3 > h4...の構造を守る）
④ 本文は PREP法（Point→Reason→Example→Point再提示）で記述
⑤ 箇条書き・表・画像を活用（ul / ol、<table>、alt付き画像を使う）
⑥ まとめ（Conclusion）で記事の要点を端的にまとめる

文字数：9000字程度
画像は必ず1つ以上含める
コード例（AWS CDK / GitHub Actionsなど）を必要に応じて含める
"""

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful technical writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=0.7,
        )
    except RateLimitError:
        print("Error: レートリミットを超えました。プランと請求情報を確認してください。", file=sys.stderr)
        sys.exit(1)
    except OpenAIError as e:
        print(f"Error: OpenAI API リクエストに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    content = resp.choices[0].message.content.strip()

    # === タイトル抽出 ===
    title = "Untitled"
    # Markdown形式 (# タイトル)
    match_md = re.search(r'^# (.+)', content, re.MULTILINE)
    # HTML形式 <title> や <h1>
    match_html = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE) or \
                 re.search(r'<h1>(.+?)</h1>', content, re.IGNORECASE)

    if match_md:
        title = match_md.group(1).strip()
    elif match_html:
        title = match_html.group(1).strip()

    # ファイル名用に整形
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    safe_title = safe_title[:50]  # 長すぎるファイル名を制限（任意）

    # Markdown ファイル保存
    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{today}-{safe_title}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Markdown saved: {filename}")
    print(f"📌 タイトル: {title}")

    # タイトルを meta/title.txt に保存（wp_post.py で使用）
    os.makedirs("meta", exist_ok=True)
    with open("meta/title.txt", "w", encoding="utf-8") as f:
        f.write(title)

if __name__ == "__main__":
    main()
