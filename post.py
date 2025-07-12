import os
import requests
import csv
from requests.auth import HTTPBasicAuth

# === 環境変数の取得 ===
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
WP_URL = os.getenv("WP_URL")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

MODEL_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

# === 関数定義 ===
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

def generate_article(keyword):
    prompt = (
        f"次のキーワードを使ってSEOに強い日本語ブログ記事を書いてください：{keyword}。\n"
        f"タイトル（30〜45文字）を最初に、次に本文（H2・H3見出しを含めて1200文字程度）を書いてください。"
    )
    res = requests.post(MODEL_URL, headers=HEADERS, json={"inputs": prompt})
    res.raise_for_status()
    return res.json()[0]['generated_text']

def post_to_wordpress(title, content):
    post = {"title": title, "content": content, "status": "publish"}
    res = requests.post(WP_URL, json=post, auth=HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD))
    print("投稿ステータス:", res.status_code)
    if res.status_code != 201:
        print(res.text)

# === メイン処理 ===
def main():
    keywords = load_keywords()
    if not keywords:
        print("投稿できるキーワードがありません。")
        return
    keyword = keywords[0]
    print("📝 投稿キーワード:", keyword)
    article = generate_article(keyword)
    title, content = article.split("\n", 1)
    post_to_wordpress(title.strip(), content.strip())
    save_posted(keyword)
    print("✅ 投稿完了")

if __name__ == "__main__":
    main()

