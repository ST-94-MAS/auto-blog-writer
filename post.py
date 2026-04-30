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


def load_keywords_files():
    """3つのキーワードファイルを読み込む"""
    base_keywords = []
    intent_keywords = []
    context_keywords = []
    
    # keywords_base.csv
    if os.path.exists("keywords_base.csv"):
        with open("keywords_base.csv", encoding="utf-8", newline="") as f:
            for line in f:
                line = line.strip()
                if line:
                    base_keywords.append(line)
    
    # keywords_intent.csv
    if os.path.exists("keywords_intent.csv"):
        with open("keywords_intent.csv", encoding="utf-8", newline="") as f:
            for line in f:
                line = line.strip()
                if line:
                    intent_keywords.append(line)
    
    # keywords_context.csv
    if os.path.exists("keywords_context.csv"):
        with open("keywords_context.csv", encoding="utf-8", newline="") as f:
            for line in f:
                line = line.strip()
                if line:
                    context_keywords.append(line)
    
    return base_keywords, intent_keywords, context_keywords


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


def build_pcombined_keywords(base_keywords, intent_keywords, context_keywords, last_base, last_intent, last_context):
    """ベース + 意図 + 文脈を組み合わせて選択"""
    # ベースキーワードを選択（前回と異なるものを優先）
    available_base = [k for k in base_keywords if k != last_base]
    if not available_base:
        available_base = base_keywords[:]
    selected_base = random.choice(available_base)
    
    # 意図キーワードを選択（前回と異なるものを優先）
    available_intent = [k for k in intent_keywords if k != last_intent]
    if not available_intent:
        available_intent = intent_keywords[:]
    selected_intent = random.choice(available_intent)
    
    # 文脈キーワードを選択（前回と異なるものを優先）
    available_context = [k for k in context_keywords if k != last_context]
    if not available_context:
        available_context = context_keywords[:]
    selected_context = random.choice(available_context)
    
    # 組み合わせたキーワード文字列を作成
    combined_keywords = [selected_base, selected_intent, selected_context]
    
    return combined_keywords, selected_base, selected_intent, selected_context
- 似たタイトルは使わず、他の記事と重ならないようにしてください。
- 同じテーマでも「初心者向け」「エラー対処」「比較」「手順」の視点を明確に区別してください。
- 以下のHTML構造を守る：
  ・<h1>タイトル（キーワード含む）</h1>
  ・導入文（<p>タグ、キーワード自然に1〜2回使用）
  ・本文は<h2><h3>構成＋PREP法（Point→Reason→Example→Point再提示）
  ・<ul> <ol> <table>など視覚的表現を活用
  ・コード例（AWS CDK / GitHub Actions など）も活用可能
  ・最後に<h2>まとめ</h2>で要点を整理してください。
"""


def generate_image_with_openai(prompt, title):
    """OpenAI DALL-E で画像を生成"""
    try:
        image_prompt = f"Create an illustration for a technical blog post titled '{title}'. The image should be professional and related to: {prompt}. Style: clean, modern, technology-focused."
        
        response = openai.Image.create(
            prompt=image_prompt,
            n=1,
            size="1024x1024"
        )
        
        image_url = response['data'][0]['url']
        return image_url
    except Exception as e:
        print(f"⚠️ 画像生成エラー: {e}", file=sys.stderr)
        return None
# 3つのキーワードファイルを読み込み
    base_keywords, intent_keywords, context_keywords = load_keywords_files()
    if not base_keywords or not intent_keywords or not context_keywords:
        print("Error: キーワードファイルが不足しています", file=sys.stderr)
        sys.exit(1)

    # 過去の履歴を読み込み（既存のkeywords.csvを使用）
    history_rows, categories, past_titles, csv_has_header = load_history_csv("keywords.csv")

    # 前回の選択を取得
    last_base = load_last_meta("last_base.txt")
    last_intent = load_last_meta("last_intent.txt")
    last_context = load_last_meta("last_context.txt")

    selected_keywords = None
    selected_base = None
    selected_intent = None
    selected_context = None
    content = None
    title = "Untitled"

    for attempt in range(6):
        # 組み合わせキーワードを選択
        selected_keywords, selected_base, selected_intent, selected_context = choose_combined_keywords(
            base_keywords, intent_keywords, context_keywords, last_base, last_intent, last_context
        )
        prompt = build_prompt(selected_keywords)

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

    # 履歴を更新
    append_history_csv({
        "title": title,
        "category": selected_base,  # ベースキーワードをカテゴリとして保存
        "theme": f"{selected_intent} {selected_context}",  # 意図+文脈をテーマとして保存
        "date": datetime.date.today().isoformat()
    }, path="keywords.csv", has_header=csv_has_header)
    
    # メタ情報を保存
    save_last_meta("last_base.txt", selected_base)
    save_last_meta("last_intent.txt", selected_intent)
    save_last_meta("last_context.txt", selected_context)
    save_last_meta("theme.txt", f"{selected_intent} {selected_context}")
    save_last_meta("category.txt", selected_base)

    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    safe_title = safe_title[:50]

    today = datetime.date.today().isoformat()
    os.makedirs("posts", exist_ok=True)
    filename = f"posts/{today}-{safe_title}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Markdown saved: {filename}")
    print(f"📌 タイトル: {title}")
    print(f"🔑 キーワード: {' '.join(selected_keywords)[:50]

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
