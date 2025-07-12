import csv
import requests
from requests.auth import HTTPBasicAuth
import os

# 環境変数から読み込む（GitHub Secretsや.env対応）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WP_URL = os.getenv("WP_URL")  # 例: https://yourblog.com/wp-json/wp/v2/posts
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# OpenAI APIキー設定
openai.api_key = OPENAI_API_KEY

def load_keywords():
    with open("keywords.csv", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    posted = set()
    if os.path.exists("posted.csv"):
        with open("posted.csv", encoding="utf-8") as f:
            posted = {line.strip() for line in f}
    return [kw for kw in keywords if kw not in posted]

def save_posted(keyword):
    with open("posted.csv", "a", encoding="utf-8") as f:
        f.write(keyword + "\n")

def generate_title(keyword):
    prompt = f"「{keyword}」をテーマに、SEOを意識した日本語のブログ記事タイトルを30〜45文字で1つ考えてください。"
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0125",
        messages=[{"role": "user", "content": prompt}]
    )
    return res["choices"][0]["message"]["content"].strip()


