#!/usr/bin/env python3
"""
HC Landscape — 人的資本経営ニュース自動収集スクリプト
=====================================================

GitHub Actionsで毎朝8時(JST)に自動実行し、
人的資本経営関連ニュースを収集→Claude APIで分類・要約→JSONに出力する。

セットアップ:
  pip install feedparser requests anthropic beautifulsoup4

環境変数:
  ANTHROPIC_API_KEY: Claude API キー

出力:
  data/news.json — フロントエンドが読み込むJSONファイル
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

# ── 設定 ──────────────────────────────────────────
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "news.json"
MAX_ARTICLES = 30  # 保持する最大記事数
DAYS_BACK = 7       # 過去何日分を取得するか

# 収集対象のRSSフィード / ニュースソース
RSS_FEEDS = [
    # Google News — 主要キーワード
    "https://news.google.com/rss/search?q=%E4%BA%BA%E7%9A%84%E8%B3%87%E6%9C%AC%E7%B5%8C%E5%96%B6&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E4%BA%BA%E6%9D%90%E6%88%A6%E7%95%A5+%E4%BC%81%E6%A5%AD&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E3%82%BF%E3%83%AC%E3%83%B3%E3%83%88%E3%83%9E%E3%83%8D%E3%82%B8%E3%83%A1%E3%83%B3%E3%83%88&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E4%B8%A1%E5%8A%B9%E3%81%8D%E3%81%AE%E7%B5%8C%E5%96%B6+%E4%BA%BA%E6%9D%90&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=%E6%96%B0%E8%A6%8F%E4%BA%8B%E6%A5%AD+%E4%BA%BA%E6%9D%90%E8%82%B2%E6%88%90&hl=ja&gl=JP&ceid=JP:ja",

    # 専門メディア
    "https://www.hrpro.co.jp/rss/",                    # HRプロ
    "https://jinjijyuku.com/feed/",                      # 人事塾
]

# キーワード（いずれかを含む記事のみ採用）
KEYWORDS = [
    "人的資本", "人材戦略", "人材育成", "タレントマネジメント",
    "リーダーシップ開発", "組織変革", "人事制度", "エンゲージメント",
    "新規事業 人材", "両効きの経営", "人的資本開示",
    "HR Tech", "ジョブ型", "リスキリング", "サクセッション",
]

# ── RSS取得 ─────────────────────────────────────
def fetch_rss_articles():
    """全RSSフィードから記事を取得"""
    articles = []
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                # 日付パース
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()

                if pub_date < cutoff:
                    continue

                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '')

                # HTMLタグを除去
                if summary:
                    summary = BeautifulSoup(summary, 'html.parser').get_text()[:300]

                # キーワードフィルタ
                text = f"{title} {summary}"
                if not any(kw in text for kw in KEYWORDS):
                    continue

                articles.append({
                    'title': title,
                    'url': link,
                    'date': pub_date.strftime('%Y-%m-%d'),
                    'raw_summary': summary,
                    'source': feed.feed.get('title', 'Unknown'),
                })
        except Exception as e:
            print(f"RSS取得エラー ({feed_url}): {e}")

    # 重複除去（タイトルベース）
    seen = set()
    unique = []
    for a in articles:
        key = re.sub(r'\s+', '', a['title'])[:30]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # 日付順にソート
    unique.sort(key=lambda x: x['date'], reverse=True)
    return unique[:MAX_ARTICLES]


# ── Claude APIで分類・要約 ─────────────────────
def classify_with_claude(articles):
    """Claude APIで記事を分類・要約する"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ANTHROPIC_API_KEY が設定されていません。分類をスキップします。")
        # フォールバック: キーワードベースの簡易分類
        return classify_by_keywords(articles)

    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    # バッチ処理（10記事ずつ）
    classified = []
    for i in range(0, len(articles), 10):
        batch = articles[i:i+10]
        articles_text = "\n\n".join([
            f"[{j+1}] タイトル: {a['title']}\n要約: {a['raw_summary'][:200]}"
            for j, a in enumerate(batch)
        ])

        prompt = f"""以下の人的資本経営関連ニュース記事を分類・要約してください。

{articles_text}

各記事について、以下のJSON配列で返してください（他の文字列は不要）:
[
  {{
    "index": 1,
    "category": "deep|explore|policy|tech のいずれか",
    "summary": "80文字以内の要約"
  }}
]

カテゴリの判定基準:
- deep（知の深化）: 既存事業の人材最適化、リーダーシップ開発、研修、評価制度、エンゲージメント向上
- explore（知の探索）: 新規事業人材育成、イノベーション、ゼロイチ、価値創造、事業開発
- policy（政策・開示）: 法規制、開示義務、伊藤レポート、経産省、金融庁、ISO30414
- tech（HR Tech）: SaaS、AI人事、タレマネシステム、データ分析、HRテクノロジー"""

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30,
            )
            data = response.json()
            text = data['content'][0]['text']

            # JSON部分を抽出
            json_match = re.search(r'\[[\s\S]*\]', text)
            if json_match:
                results = json.loads(json_match.group())
                for r in results:
                    idx = r['index'] - 1
                    if 0 <= idx < len(batch):
                        batch[idx]['cat'] = r.get('category', 'deep')
                        batch[idx]['summary'] = r.get('summary', batch[idx]['raw_summary'][:80])

        except Exception as e:
            print(f"Claude API エラー: {e}")

        classified.extend(batch)

    # summaryがないものにフォールバック
    for a in classified:
        if 'cat' not in a:
            a['cat'] = classify_single_by_keywords(a)
        if 'summary' not in a:
            a['summary'] = a['raw_summary'][:80]

    return classified


def classify_by_keywords(articles):
    """キーワードベースの簡易分類（APIなしフォールバック）"""
    for a in articles:
        a['cat'] = classify_single_by_keywords(a)
        a['summary'] = a['raw_summary'][:80]
    return articles


def classify_single_by_keywords(article):
    """1記事をキーワードで分類"""
    text = f"{article['title']} {article.get('raw_summary','')}"
    if any(kw in text for kw in ['経産省', '金融庁', '開示', '伊藤レポート', 'ISO', '法制', 'ガイドライン']):
        return 'policy'
    if any(kw in text for kw in ['SaaS', 'AI', 'テック', 'Tech', 'システム', 'プラットフォーム', 'データ']):
        return 'tech'
    if any(kw in text for kw in ['新規事業', 'イノベーション', 'ゼロイチ', '価値創造', '探索', '起業']):
        return 'explore'
    return 'deep'


# ── JSON出力 ─────────────────────────────────────
def save_json(articles):
    """news.json に出力"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "last_updated": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+09:00'),
        "total": len(articles),
        "articles": [
            {
                "date": a['date'],
                "title": a['title'],
                "summary": a.get('summary', ''),
                "cat": a.get('cat', 'deep'),
                "source": a.get('source', ''),
                "url": a.get('url', '#'),
            }
            for a in articles
        ]
    }

    # 既存ファイルとマージ（重複除去）
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding='utf-8'))
            existing_titles = {a['title'] for a in existing.get('articles', [])}
            for a in output['articles']:
                if a['title'] not in existing_titles:
                    existing['articles'].insert(0, a)
            existing['articles'] = existing['articles'][:MAX_ARTICLES]
            existing['last_updated'] = output['last_updated']
            existing['total'] = len(existing['articles'])
            output = existing
        except Exception:
            pass

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"✅ {len(output['articles'])}件の記事を {OUTPUT_FILE} に保存しました")


# ── メイン ───────────────────────────────────────
def main():
    print("=" * 50)
    print("HC Landscape — ニュース自動収集")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    print("\n📡 RSSフィードを取得中...")
    articles = fetch_rss_articles()
    print(f"  → {len(articles)}件の記事を取得")

    if not articles:
        print("⚠️ 新しい記事が見つかりませんでした")
        return

    print("\n🤖 Claude APIで分類・要約中...")
    classified = classify_with_claude(articles)
    print(f"  → {len(classified)}件を分類完了")

    # カテゴリ別カウント
    cats = {}
    for a in classified:
        c = a.get('cat', 'deep')
        cats[c] = cats.get(c, 0) + 1
    cat_names = {'deep':'知の深化','explore':'知の探索','policy':'政策・開示','tech':'HR Tech'}
    for c, count in sorted(cats.items()):
        print(f"    {cat_names.get(c,c)}: {count}件")

    print("\n💾 JSONファイルを出力中...")
    save_json(classified)
    print("\n✅ 完了！")


if __name__ == "__main__":
    main()
