#!/usr/bin/env python3
# post.py

import os
import sys
import datetime
import csv
import glob
import time
import difflib
from dotenv import load_dotenv
import openai
import random
import re
from openai.error import RateLimitError, OpenAIError

def normalize_text(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def extract_title(content):
    match_md = re.search(r'^#\s*(.+)', content, re.MULTILINE)
    match_html = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE) or \
                 re.search(r'<h1>(.+?)</h1>', content, re.IGNORECASE)
    if match_md:
        return match_md.group(1).strip()
    if match_html:
        return match_html.group(1).strip()
    return None


def title_similarity(a, b):
    if not a or not b:
        return 0.0
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    return difflib.SequenceMatcher(None, a_norm, b_norm).ratio()


def is_similar_title(title, existing_titles, threshold=0.72):
    for past_title in existing_titles:
        if title_similarity(title, past_title) >= threshold:
            return True
    return False


def load_history_csv(path="keywords.csv"):
    if not os.path.exists(path):
        print(f"Error: {path} が見つかりません", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample)
        f.seek(0)

        rows = []
        categories = []
        titles = []

        if has_header:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
                category = row.get("category", "")
                title = row.get("title", "")
                theme = row.get("theme", "")
                date = row.get("date", "")
                rows.append({"title": title, "category": category, "theme": theme, "date": date})
                if category:
                    categories.append(category)
                if title:
                    titles.append(title)
        else:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                category = row[0].strip()
                rows.append({"title": "", "category": category, "theme": "", "date": ""})
                categories.append(category)

    return rows, categories, titles, has_header


def append_history_csv(record, path="keywords.csv", has_header=False):
    fieldnames = ["title", "category", "theme", "date"]

    if has_header:
        with open(path, encoding="utf-8", newline="", mode="a") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(record)
        return

    # 旧形式のファイルをヘッダー付きDB形式に変換して追記
    existing_rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            existing_rows.append({"title": "", "category": row[0].strip(), "theme": "", "date": ""})

    with open(path, encoding="utf-8", newline="", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerow(record)


def load_last_meta(name):
    path = os.path.join("meta", name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_last_meta(name, value):
    os.makedirs("meta", exist_ok=True)
    with open(os.path.join("meta", name), "w", encoding="utf-8") as f:
        f.write(value)


def choose_topic(categories, last_category):
    available = [c for c in categories if c != last_category]
    if not available:
        available = categories[:]
    category_keyword = random.choice(available)
    other_keywords = [c for c in categories if c != category_keyword]
    num_extra = random.randint(0, min(3, len(other_keywords)))
    selected = [category_keyword] + random.sample(other_keywords, k=num_extra)
    return selected


def choose_theme(previous_theme):
    theme_types = ["初心者向け", "エラー対処", "比較", "手順"]
    available = [t for t in theme_types if t != previous_theme]
    return random.choice(available) if available else random.choice(theme_types)


def build_prompt(keywords, theme_type):
    keyword_str = ", ".join(keywords)
    return f"""
あなたはプロの日本語技術ブログライターです。
以下の条件に基づき、HTML形式のWordPress用記事を書いてください。

【キーワード】{keyword_str}
【切り口】{theme_type}

【条件】
- <html> や <head> は出力しないでください（<body>内のコンテンツのみ）
- WordPress の HTML編集モードに直接貼り付けられる形式で書いてください
- できる限り記載してください。
- 指定したキーワードはテーマとして活用するが、タイトルと本文では完全一致の文字列を避け、類義語や言い換えで表現してください。
- 過去30記事と近いタイトル・内容にならないよう、新しい視点と切り口を意識してください。
- 似たタイトルは使わず、他の記事と重ならないようにしてください。
- 同じテーマでも「初心者向け」「エラー対処」「比較」「手順」の視点を明確に区別してください。
- 以下のHTML構造を守る：
  ・<h1>タイトル（キーワード含む）</h1>
  ・導入文（<p>タグ、キーワード自然に1〜2回使用）
  ・本文は<h2><h3>構成＋PREP法（Point→Reason→Example→Point再提示）
  ・<ul> <ol> <table>など視覚的表現を活用
  ・コード例（AWS CDK / GitHub Actions など）も活用可能
  ・最後に<h2>まとめ</h2>で要点を整理してください
"""


def call_openai_with_retry(prompt, max_retries=3):
    """OpenAI API を呼び出し、エラー時はリトライする"""
    for attempt in range(max_retries):
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
            return resp
        except RateLimitError as e:
            print(f"⚠️ レートリミット（リトライ {attempt + 1}/{max_retries}）: {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                raise
            wait_time = 5 * (attempt + 1)
            print(f"⏳ {wait_time}秒待機中...", file=sys.stderr)
            time.sleep(wait_time)
        except OpenAIError as e:
            print(f"⚠️ API エラー（リトライ {attempt + 1}/{max_retries}）: {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                raise
            wait_time = 5 * (attempt + 1)
            print(f"⏳ {wait_time}秒待機中...", file=sys.stderr)
            time.sleep(wait_time)

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: 環境変数 OPENAI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key

    history_rows, categories, past_titles, csv_has_header = load_history_csv("keywords.csv")
    if not categories:
        print("Error: keywords.csv にカテゴリ情報がありません", file=sys.stderr)
        sys.exit(1)

    last_category = history_rows[-1].get("category") if history_rows and history_rows[-1].get("category") else load_last_meta("last_category.txt")
    last_theme = history_rows[-1].get("theme") if history_rows and history_rows[-1].get("theme") else load_last_meta("last_theme.txt")

    selected_keywords = None
    selected_theme = None
    content = None
    title = "Untitled"

    for attempt in range(6):
        selected_keywords = choose_topic(categories, last_category)
        selected_theme = choose_theme(last_theme)
        prompt = build_prompt(selected_keywords, selected_theme)

        try:
            resp = call_openai_with_retry(prompt)
        except (RateLimitError, OpenAIError) as e:
            print(f"Error: OpenAI API リクエストが失敗しました（3回のリトライ後）: {e}", file=sys.stderr)
            sys.exit(1)

        content = resp.choices[0].message.content.strip()
        title = extract_title(content) or "Untitled"

        if title == "Untitled":
            print(f"⚠️ タイトルが抽出できませんでした。リトライ {attempt + 1}/6", file=sys.stderr)
            continue
        if is_similar_title(title, past_titles):
            print(f"⚠️ 類似タイトルが検出されました: {title}. リトライ {attempt + 1}/6", file=sys.stderr)
            continue
        break

    if not content or title == "Untitled":
        print("Error: 適切な記事タイトルを持つコンテンツを生成できませんでした", file=sys.stderr)
        sys.exit(1)

    category = selected_keywords[0]
    append_history_csv({
        "title": title,
        "category": category,
        "theme": selected_theme,
        "date": datetime.date.today().isoformat()
    }, path="keywords.csv", has_header=csv_has_header)
    save_last_meta("last_category.txt", category)
    save_last_meta("last_theme.txt", selected_theme)
    save_last_meta("theme.txt", selected_theme)
    save_last_meta("category.txt", category)

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
