#!/usr/bin/env python3
# post.py - ChatGPT によるブログ記事自動生成スクリプト

import os
import sys
import datetime
import csv
import re
import random
from dotenv import load_dotenv
import openai
from openai.error import RateLimitError, OpenAIError

def main():
    # 環境変数ロード
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY が未設定です", file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key

    # キーワード読込
    try:
        with open("keywords.csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            keywords = [row[0].strip() for row in reader if row]
    except FileNotFoundError:
        print("❌ Error: keywords.csv が見つかりません", file=sys.stderr)
        sys.exit(1)
    if not keywords:
        print("❌ Error: keywords.csv にキーワードがありません", file=sys.stderr)
        sys.exit(1)

    selected_keywords = random.sample(keywords, k=random.randint(1, 4))
    keyword = ", ".join(selected_keywords)

    # プロンプト作成
    prompt = f"""
あなたはプロの技術ブログライターです。
以下のキーワードに沿って、WordPress 用の記事を日本語で執筆してください。

・キーワード: {keyword}
・WordPressのHTML編集モードに貼れる形式で書いてください（コードや表はHTMLタグ形式）。
・① タイトル（h1）検索キーワードを含める
・② 導入文（リード文）キーワードを自然に1～2回含める
・③ 見出し構成（h2 > h3 > h4...の構造を守る）
・④ 本文（PREP法：Point→Reason→Example→Point再提示）
・⑤ 箇条書き、表、画像（alt付き推奨）で視覚的に整理
・⑥ まとめ：要点を端的に
・9000文字程度で生成する
・AI生成画像を最低1つ入れる（alt属性付きでも良い）
・手順やステップは 1、2、3 など明示的に記載
・コードスニペット（AWS CDK や GitHub Actions など）も適宜含める
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful technical writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=0.7,
        )
    except RateLimitError:
        print("❌ Error: レートリミットを超過しました", file=sys.stderr)
        sys.exit(1)
    except OpenAIError as e:
        print(f"❌ Error: OpenAI API エラー: {e}", file=sys.stderr)
        sys.exit(1)

    content = response.choices[0].message.content.strip()

    # タイトル抽出（# または先頭非空行）
    lines = content.splitlines()
    title = "Untitled"
    for line in lines:
        if line.strip().startswith("# "):
            title = line.strip()[2:].strip()
            break
    else:
        for line in lines:
            if line.strip():
                title = line.strip()[:50]
                break

    # スラッグ生成
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    safe_title = safe_title[:50]

    # ファイル保存
    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{today}-{safe_title}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Markdown saved: {filename}")
    print(f"📌 タイトル: {title}")

    # WordPress用タイトル保存
    os.makedirs("meta", exist_ok=True)
    with open("meta/title.txt", "w", encoding="utf-8") as f:
        f.write(title)

if __name__ == "__main__":
    main()
