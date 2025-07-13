import os
import datetime
import csv
import openai

# OpenAI API キーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# キーワード CSV を読み込んでランダムに選択（例）
with open("keywords.csv", encoding="utf-8") as f:
    reader = csv.reader(f)
    keywords = [row[0] for row in reader if row]
keyword = keywords[datetime.date.today().day % len(keywords)]

# プロンプトを組み立て
prompt = f"""
あなたはプロの技術ブログライターです。
以下のキーワードに沿って、WordPress 用の記事を日本語で執筆してください。
・キーワード: {keyword}
・構成: 見出し（h2,h3）を含む
・コードスニペット: 必要に応じて AWS CDK や GitHub Actions の例を挿入
"""

# ChatGPT（gpt-4）に投げる
resp = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful technical writer."},
        {"role": "user",   "content": prompt}
    ],
    max_tokens=2000,
    temperature=0.7,
)

content = resp.choices[0].message.content

# Markdown ファイルとして保存
today = datetime.date.today().isoformat()
os.makedirs("posts", exist_ok=True)
filename = f"posts/{today}-{keyword}.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Generated: {filename}")
