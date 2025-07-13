#!/usr/bin/env python3
# post.py
import os
import datetime
import csv
from dotenv import load_dotenv
import openai

def main():
    # .env ファイルから環境変数を読み込む
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 OPENAI_API_KEY が設定されていません")

    # OpenAI API キーをセット
    openai.api_key = api_key

    # キーワード CSV を読み込んでリスト化
    with open("keywords.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        keywords = [row[0].strip() for row in reader if row]
    if not keywords:
        raise RuntimeError("keywords.csv にキーワードがありません")

    # 今日の日付をインデックス代わりにしてキーワードを選択
    keyword = keywords[datetime.date.today().day % len(keywords)]

    # プロンプトを組み立て
    prompt = f"""
あなたはプロの技術ブログライターです。
以下のキーワードに沿って、WordPress 用の記事を日本語で執筆してください。
・キーワード: {keyword}
・構成: 見出し（h2, h3）を含む
・コードスニペット: 必要に応じて AWS CDK や GitHub Actions の例を挿入
"""

    # ChatGPT に投げて生成
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful technical writer."},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    content = resp.choices[0].message.content

    # posts/ フォルダに Markdown ファイルで保存
    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{today}-{keyword}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {filename}")

if __name__ == "__main__":
    main()
