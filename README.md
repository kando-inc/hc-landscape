# HC Landscape（Claude版）

**人的資本経営ソリューション完全ガイド — AI制作 by Anthropic Claude**

人的資本経営を支える国内主要21社を「既存事業の深化 × 価値創造」の2軸で独自にマッピングした業界ガイドサイトです。

🔗 **公開URL**: [https://kando-inc.github.io/hc-landscape/] （GitHub Pages）

---

## 構成

```
hc-landscape/
├── index.html              # メインサイト（単一HTML、CSS/JS含む）
├── 404.html                # 404エラーページ
├── sitemap.xml             # SEO用サイトマップ
├── robots.txt              # クローラー制御
├── CNAME                   # カスタムドメイン設定
├── .nojekyll               # Jekyll処理をスキップ
├── data/
│   └── news.json           # ニュースフィードデータ（自動更新）
├── scripts/
│   └── news_crawler.py     # ニュース自動収集スクリプト
└── .github/
    └── workflows/
        └── news-crawler.yml  # GitHub Actions（日次ニュース収集）
```

## セットアップ

### 1. GitHub Pagesの有効化

1. リポジトリの **Settings** → **Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / `/ (root)`
4. **Save**

### 2. カスタムドメインの設定

1. ドメインレジストラで `hc-landscape.jp` を取得
2. DNS設定で以下のレコードを追加:
   ```
   CNAME  www   → <username>.github.io
   A      @     → 185.199.108.153
   A      @     → 185.199.109.153
   A      @     → 185.199.110.153
   A      @     → 185.199.111.153
   ```
3. リポジトリ Settings → Pages → Custom domain に `hc-landscape.jp` を入力
4. **Enforce HTTPS** にチェック

### 3. ニュース自動収集の設定

1. [Anthropic Console](https://console.anthropic.com/) でAPIキーを取得
2. リポジトリ **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** で `ANTHROPIC_API_KEY` を追加
4. Actions タブ → `Daily News Crawler` → **Enable workflow**

手動実行テスト: Actions → `Daily News Crawler` → **Run workflow**

### 4. Google Search Console

1. [Search Console](https://search.google.com/search-console) でプロパティを追加
2. DNS TXTレコードで所有権を確認
3. サイトマップ `https://hc-landscape.jp/sitemap.xml` を送信

### 5. GA4（任意）

index.html の `</head>` 直前に gtag.js スニペットを追加。

---

## ニュース自動収集の仕組み

```
毎朝8時(JST) → GitHub Actions起動
  → scripts/news_crawler.py 実行
    → Google News RSS + HR専門メディアから記事取得
    → Claude API で分類（深化/探索/政策/HR Tech）・要約
    → data/news.json に出力
  → 自動コミット・デプロイ
```

---

## 技術スタック

- **フロントエンド**: 単一HTML（Vanilla JS + CSS、フレームワーク不使用）
- **フォント**: Noto Sans JP / Noto Serif JP（Google Fonts）
- **ホスティング**: GitHub Pages（静的配信）
- **ニュース収集**: Python + feedparser + Claude API
- **CI/CD**: GitHub Actions（日次cron）

---

## SEO実装

- title/meta description/keywords 最適化
- OGP（7タグ）+ Twitter Card
- JSON-LD: Article + FAQPage（3問）+ BreadcrumbList
- セマンティックHTML（main/article/section/aside/nav）
- canonical URL
- sitemap.xml + robots.txt
- preconnect for Google Fonts

---

## クレジット

- **企画・制作**: Claude（Anthropic）
- **運営**: KANDO株式会社

---

## ライセンス

© 2026 HC Landscape. All rights reserved.
