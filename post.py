#!/usr/bin/env python3
# post.py

import os
import sys
import datetime
import csv
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
    # <h1>, <h1 class="..."> の両方に対応
    match_html = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
    if match_html:
        title = re.sub(r"<[^>]+>", "", match_html.group(1))
        return title.strip()

    # Markdown見出しにも対応
    match_md = re.search(r"^#\s*(.+)", content, re.MULTILINE)
    if match_md:
        return match_md.group(1).strip()

    return None


def title_similarity(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def is_similar_title(title, existing_titles, threshold=0.72):
    return any(title_similarity(title, past_title) >= threshold for past_title in existing_titles)


def load_history_csv(path="keywords.csv"):
    if not os.path.exists(path):
        fallback = "keywords_base.csv"
        if os.path.exists(fallback):
            print(f"Warning: {path} が見つかりません。{fallback} をカテゴリソースとして使用します。", file=sys.stderr)
            path = fallback
        else:
            print(f"Error: {path} が見つかりません", file=sys.stderr)
            sys.exit(1)

    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(2048)
        f.seek(0)

        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = False

        rows = []
        categories = []
        titles = []

        if has_header:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
                title = row.get("title", "")
                category = row.get("category", "")
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
                if category:
                    rows.append({"title": "", "category": category, "theme": "", "date": ""})
                    categories.append(category)

    return rows, categories, titles, has_header


def append_history_csv(record, path="keywords.csv", has_header=False):
    fieldnames = ["title", "category", "theme", "date"]

    if not os.path.exists(path):
        with open(path, encoding="utf-8", newline="", mode="w") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(record)
        return

    if has_header:
        with open(path, encoding="utf-8", newline="", mode="a") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(record)
        return

    existing_rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            existing_rows.append({
                "title": "",
                "category": row[0].strip(),
                "theme": "",
                "date": ""
            })

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

    return [category_keyword] + random.sample(other_keywords, k=num_extra)


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
- <html> や <head> は出力しないでください。
- WordPress の HTML編集モードに直接貼り付けられる形式で書いてください。
- 冒頭に必ず <h1>記事タイトル</h1> を1つだけ書いてください。
- タイトルは日本語で、検索されやすく、具体的な内容にしてください。
- 本文は必ず1000文字以上を目安にしてください。
- 導入文は <p> タグで書いてください。
- 本文は <h2> と <h3> を使って構成してください。
- PREP法（Point→Reason→Example→Point再提示）を意識してください。
- <ul>, <ol>, <table>, <pre><code> などを必要に応じて使ってください。
- AWS、AI、GitHub Actions、WordPress、自動化などの具体例を含めてください。
- 最後に必ず <h2>まとめ</h2> を作り、要点を整理してください。
- 本文だけを出力してください。説明文や前置きは不要です。
"""


def call_openai_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful Japanese technical blog writer."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=8192,
                temperature=0.7,
            )

        except RateLimitError as e:
            print(f"⚠️ レートリミット（リトライ {attempt + 1}/{max_retries}）: {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                raise
            time.sleep(5 * (attempt + 1))

        except OpenAIError as e:
            print(f"⚠️ APIエラー（リトライ {attempt + 1}/{max_retries}）: {e}", file=sys.stderr)
            if attempt == max_retries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def ensure_content_has_h1(content, title):
    if "<h1" not in content.lower():
        return f"<h1>{title}</h1>\n\n{content}"
    return content


def make_safe_filename(title):
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "-")
    safe_title = safe_title[:50]
    if not safe_title:
        safe_title = f"article-{int(time.time())}"
    return safe_title


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

    last_category = (
        history_rows[-1].get("category")
        if history_rows and history_rows[-1].get("category")
        else load_last_meta("last_category.txt")
    )

    last_theme = (
        history_rows[-1].get("theme")
        if history_rows and history_rows[-1].get("theme")
        else load_last_meta("last_theme.txt")
    )

    content = None
    title = None
    selected_keywords = None
    selected_theme = None

    for attempt in range(6):
        selected_keywords = choose_topic(categories, last_category)
        selected_theme = choose_theme(last_theme)
        prompt = build_prompt(selected_keywords, selected_theme)

        try:
            resp = call_openai_with_retry(prompt)
        except (RateLimitError, OpenAIError) as e:
            print(f"Error: OpenAI API リクエストが失敗しました: {e}", file=sys.stderr)
            sys.exit(1)

        content = resp.choices[0].message.content.strip()

        if not content:
            print(f"⚠️ 本文が空です。リトライ {attempt + 1}/6", file=sys.stderr)
            continue

        title = extract_title(content)

        if not title:
            print("⚠️ タイトル抽出失敗 → 仮タイトルを付与して保存します", file=sys.stderr)
            title = f"{selected_keywords[0]}の記事-{int(time.time())}"
            content = ensure_content_has_h1(content, title)

        if len(content) < 500:
            print(f"⚠️ 本文が短すぎます。リトライ {attempt + 1}/6", file=sys.stderr)
            continue

        if is_similar_title(title, past_titles):
            print(f"⚠️ 類似タイトルが検出されました: {title}. リトライ {attempt + 1}/6", file=sys.stderr)
            continue

        break

    if not content:
        print("Error: 本文を生成できませんでした", file=sys.stderr)
        sys.exit(1)

    if not title:
        title = f"article-{int(time.time())}"
        content = ensure_content_has_h1(content, title)

    category = selected_keywords[0] if selected_keywords else "未分類"
    theme = selected_theme or "未設定"

    append_history_csv({
        "title": title,
        "category": category,
        "theme": theme,
        "date": datetime.date.today().isoformat()
    }, path="keywords.csv", has_header=csv_has_header)

    save_last_meta("last_category.txt", category)
    save_last_meta("last_theme.txt", theme)
    save_last_meta("theme.txt", theme)
    save_last_meta("category.txt", category)

    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)

    filename = f"posts/{today}-{make_safe_filename(title)}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    os.makedirs("meta", exist_ok=True)

    with open("meta/title.txt", "w", encoding="utf-8") as f:
        f.write(title)

    print(f"✅ Markdown saved: {filename}")
    print(f"📌 タイトル: {title}")
    print(f"🔑 キーワード: {', '.join(selected_keywords or [])}")
    print(f"🎯 切り口: {theme}")


if __name__ == "__main__":
    main()