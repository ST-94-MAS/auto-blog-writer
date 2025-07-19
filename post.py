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

    # プロンプトを組み立て
    prompt = f"""
あなたはプロの技術ブログライターです。
以下のキーワードに沿って、WordPress 用の記事を日本語で執筆してください。
・キーワード: {keyword}
・WordPressのHTML編集モードに貼れる形式で書いてください。コードや表はHTMLタグ形式で記述してください。
・① タイトル（h1）検索キーワードを含める
・② 導入文（リード文）キーワードを自然に1～2回含める
・③ 見出し構成（h2 > h3 > h4...の構造を守って)
・④ 本文（各見出しの中）PREP法（Point→Reason→Example→Point再提示）が有効
・⑤ 箇条書き・表・画像を活用情報を視覚的に整理（ユーザー滞在時間UP・直帰率低下）
    ul / ol タグや <table> 使用推奨
    alt属性付き画像はSEOに有利
・⑥ まとめ（Conclusion）記事の要点を端的にまとめる
・9000文字くらいで作成して
・画像は一つは必ず入れて(alt属性付き画像ではなくAIが生成した画像でいい)
・手順などあれば詳細に1、２、３と記載して
・コードスニペット: 必要に応じて AWS CDK や GitHub Actions の例を挿入
"""

    # ChatGPT に投げる
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

    # === タイトル抽出（最初の "# " から取得）===
    first_line = content.splitlines()[0]
    if first_line.startswith("# "):
        title = first_line[2:].strip()
    else:
        title = "Untitled"

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

    # タイトルを meta/title.txt に保存（wp_post.py で使用するため）
    os.makedirs("meta", exist_ok=True)
    with open("meta/title.txt", "w", encoding="utf-8") as f:
        f.write(title)

if __name__ == "__main__":
    main()
