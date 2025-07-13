i# .github/workflows/post.yml の一例
name: 自動ポスト生成

on:
  workflow_dispatch:

jobs:
  generate_and_deploy:
    runs-on: ubuntu-latest

    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      WP_URL:          ${{ secrets.WP_URL }}
      WP_USERNAME:     ${{ secrets.WP_USERNAME }}
      WP_APP_PASSWORD: ${{ secrets.WP_APP_PASSWORD }}

    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python セットアップ
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: 依存パッケージをインストール
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: 記事を生成
        run: |
          python post.py

      - name: WordPress に投稿
        run: |
          # 生成された Markdown を HTML に変換して投稿する例
          pip install markdown requests
          python << 'EOF'
import os, glob, markdown, requests
# 最新ファイルを取得
md = sorted(glob.glob("posts/*.md"))[-1]
html = markdown.markdown(open(md, encoding="utf-8").read())
resp = requests.post(
    f"{os.getenv('WP_URL')}/wp-json/wp/v2/posts",
    auth=(os.getenv('WP_USERNAME'), os.getenv('WP_APP_PASSWORD')),
    json={"title": md, "content": html, "status": "publish"}
)
resp.raise_for_status()
print("Posted:", resp.json()["link"])
EOF

      - name: コミット＆プッシュ（必要なら）
        run: |
          git add posts/
          git diff --quiet || git commit -m "chore: 新規記事を自動投稿"
          git push
