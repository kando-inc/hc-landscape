#!/usr/bin/env python3
"""
HC Landscape — 人的資本経営ニュース自動収集スクリプト（v4）
============================================================

ソース方針：
  一次情報源＋質の高いビジネスメディア・専門メディアから取得。
  Google Newsのような集約サイトは使わない。

全28ソース体制：
  官公庁5 / コンサル4 / シンクタンク7 / 経済団体1 /
  HR専門メディア3 / ビジネス誌5 / HR Tech3
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import socket
socket.setdefaulttimeout(15)  # 15秒で各RSS取得を打ち切り
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "news.json"
MAX_ARTICLES = 30
DAYS_BACK = 14

SOURCES = [
    # ═══ 官公庁・政策機関（5） ═══
    {"name": "経済産業省",
     "url": "https://www.meti.go.jp/press/index.rdf",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "人材", "経営", "開示", "伊藤レポート", "リスキリング"]},
    {"name": "金融庁",
     "url": "https://www.fsa.go.jp/news/index.rdf",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "開示", "有価証券", "ガバナンス", "サステナビリティ"]},
    {"name": "厚生労働省",
     "url": "https://www.mhlw.go.jp/stf/news.rdf",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "リスキリング", "人材開発", "キャリア形成", "職業能力開発", "人材育成"]},
    {"name": "内閣官房",
     "url": "https://www.cas.go.jp/jp/rss/index.xml",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "新しい資本主義", "人材", "リスキリング", "賃上げ"]},
    {"name": "JILPT（労働政策研究・研修機構）",
     "url": "https://www.jil.go.jp/kokunai/blt/index.rdf",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "人材", "雇用", "労働", "人への投資", "リスキリング", "キャリア"]},

    # ═══ コンサルファーム Insights（4） ═══
    {"name": "デロイト トーマツ",
     "url": "https://www2.deloitte.com/jp/ja/pages/human-capital/articles/hcm.rss.xml",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材", "組織", "リーダーシップ", "イノベーション", "新規事業"]},
    {"name": "PwC Japan",
     "url": "https://www.pwc.com/jp/ja/knowledge/rss.xml",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材", "新規事業", "組織変革", "タレント", "リスキリング"]},
    {"name": "EY Japan",
     "url": "https://www.ey.com/ja_jp/rss-feeds/news",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材", "サステナビリティ", "イノベーション", "組織"]},
    {"name": "コーン・フェリー",
     "url": "https://www.kornferry.com/ja/insights.rss",
     "trust": 4, "hint": "deep",
     "keywords": ["リーダーシップ", "人材", "アセスメント", "組織", "報酬", "タレント"]},

    # ═══ シンクタンク（7） ═══
    {"name": "リクルートワークス研究所",
     "url": "https://www.works-i.com/research/feed/",
     "trust": 5, "hint": "deep",
     "keywords": ["人材", "働き方", "組織", "雇用", "人的資本", "リーダー"]},
    {"name": "パーソル総合研究所",
     "url": "https://rc.persol-group.co.jp/rss.xml",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材", "組織", "エンゲージメント", "リスキリング", "タレント"]},
    {"name": "日本総合研究所",
     "url": "https://www.jri.co.jp/MediaLibrary/file/report/rss.xml",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "人材", "雇用", "働き方", "賃金", "組織", "経営", "イノベーション"]},
    {"name": "三菱総合研究所",
     "url": "https://www.mri.co.jp/knowledge/rss.xml",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本", "人材", "雇用", "DX", "イノベーション", "組織", "リスキリング"]},
    {"name": "野村総合研究所",
     "url": "https://www.nri.com/jp/knowledge/rss.xml",
     "trust": 5, "hint": "deep",
     "keywords": ["人材", "人的資本", "DX", "組織", "働き方", "イノベーション", "経営"]},
    {"name": "みずほリサーチ＆テクノロジーズ",
     "url": "https://www.mizuho-rt.co.jp/publication/rss.xml",
     "trust": 4, "hint": "policy",
     "keywords": ["人的資本", "人材", "雇用", "賃金", "労働", "リスキリング"]},
    {"name": "大和総研",
     "url": "https://www.dir.co.jp/report/rss.xml",
     "trust": 4, "hint": "policy",
     "keywords": ["人的資本", "人材", "開示", "ガバナンス", "ESG", "サステナビリティ"]},

    # ═══ 経済団体（1） ═══
    {"name": "経団連",
     "url": "https://www.keidanren.or.jp/rss.xml",
     "trust": 5, "hint": "policy",
     "keywords": ["人材", "人的資本", "雇用", "教育", "リスキリング", "イノベーション"]},

    # ═══ HR専門メディア（3） ═══
    {"name": "HRpro",
     "url": "https://www.hrpro.co.jp/rss/",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本経営", "タレントマネジメント", "組織開発", "エンゲージメント", "新規事業 人材", "リーダーシップ"]},
    {"name": "日本の人事部",
     "url": "https://jinjibu.jp/rss/index.xml",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材育成", "組織開発", "エンゲージメント", "タレント", "リスキリング", "サクセッション"]},
    {"name": "@人事",
     "url": "https://at-jinji.jp/feed",
     "trust": 3, "hint": "deep",
     "keywords": ["人的資本経営", "人材戦略", "組織変革", "エンゲージメント", "タレントマネジメント"]},

    # ═══ ビジネス誌・新聞・経営誌（5） ═══
    {"name": "日経ビジネス",
     "url": "https://business.nikkei.com/rss/sns/nb.rdf",
     "trust": 5, "hint": "deep",
     "keywords": ["人的資本", "人材戦略", "CHRO", "リスキリング", "新規事業 人材", "組織変革", "タレント", "エンゲージメント"]},
    {"name": "東洋経済オンライン",
     "url": "https://toyokeizai.net/list/feed/rss",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材育成", "リーダーシップ", "新規事業", "組織改革", "CHRO", "タレント"]},
    {"name": "ダイヤモンド・オンライン",
     "url": "https://diamond.jp/feed/index.xml",
     "trust": 4, "hint": "deep",
     "keywords": ["人的資本", "人材戦略", "リスキリング", "新規事業", "組織", "CHRO", "タレントマネジメント"]},
    {"name": "日経電子版",
     "url": "https://www.nikkei.com/rss/index.rdf",
     "trust": 5, "hint": "policy",
     "keywords": ["人的資本経営", "人材投資", "人的資本開示", "CHRO"]},
    {"name": "Harvard Business Review 日本版",
     "url": "https://dhbr.diamond.jp/list/feed/rss",
     "trust": 5, "hint": "deep",
     "keywords": ["リーダーシップ", "人材", "組織", "イノベーション", "マネジメント", "人的資本"]},

    # ═══ HR Tech 企業プレスリリース（3） ═══
    {"name": "カオナビ",
     "url": "https://corp.kaonavi.jp/press/feed/",
     "trust": 4, "hint": "tech",
     "keywords": ["タレントマネジメント", "人材", "配置", "AI", "機能"]},
    {"name": "SmartHR",
     "url": "https://smarthr.jp/feed/",
     "trust": 4, "hint": "tech",
     "keywords": ["人事", "労務", "タレント", "サーベイ", "エンゲージメント"]},
    {"name": "タレントパレット",
     "url": "https://www.talent-palette.com/news/feed/",
     "trust": 4, "hint": "tech",
     "keywords": ["タレントマネジメント", "人材", "AI", "データ分析", "配置", "育成"]},
]


def fetch_articles():
    articles = []
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)
    for source in SOURCES:
        try:
            feed = feedparser.parse(source["url"], request_headers={"User-Agent":"HC-Landscape-Bot/1.0"})
            count = 0
            for entry in feed.entries[:30]:
                pub_date = None
                for attr in ['published_parsed', 'updated_parsed']:
                    parsed = getattr(entry, attr, None)
                    if parsed:
                        pub_date = datetime(*parsed[:6])
                        break
                if not pub_date:
                    pub_date = datetime.now()
                if pub_date < cutoff:
                    continue
                title = entry.get('title', '').strip()
                link = entry.get('link', '')
                summary = entry.get('summary', '')
                if summary:
                    summary = BeautifulSoup(summary, 'html.parser').get_text()[:500]
                text = f"{title} {summary}"
                if not any(kw in text for kw in source["keywords"]):
                    continue
                articles.append({
                    'title': title, 'url': link,
                    'date': pub_date.strftime('%Y-%m-%d'),
                    'raw_summary': summary,
                    'source': source["name"],
                    'trust': source["trust"],
                    'hint': source["hint"],
                })
                count += 1
                if count >= 5:
                    break
            print(f"  ✓ {source['name']}: {count}件")
        except Exception as e:
            print(f"  ✗ {source['name']}: エラー ({e})")
    seen = set()
    unique = []
    for a in articles:
        key = re.sub(r'\s+', '', a['title'])[:30]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    unique.sort(key=lambda x: x['date'], reverse=True)
    return unique[:MAX_ARTICLES * 3]


def curate_with_claude(articles):
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("  ANTHROPIC_API_KEY未設定。キーワードベースで分類します。")
        return fallback_classify(articles)
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    articles_text = "\n\n".join([
        f"[{i+1}] 出典: {a['source']}（信頼度{a['trust']}）\nタイトル: {a['title']}\n概要: {a['raw_summary'][:200]}"
        for i, a in enumerate(articles)
    ])
    prompt = f"""あなたは「HC Landscape」という人的資本経営の業界ガイドサイトの編集者です。
このサイトのテーマは「人を活かして価値を創造する」です。以下の記事候補から、大企業の役員・経営企画部長・CHRO が読む価値のある記事だけを厳選してください。

■ 採用すべき記事の例:
- 人材戦略・人材ポートフォリオに関する経営レベルの議論
- リーダーシップ開発・次世代経営人材の育成に関する知見
- エンゲージメント向上・組織開発の先進事例や調査結果
- タレントマネジメント・サクセッションプランの実践
- 新規事業を担う人材の育成・イノベーション人材の確保
- 人的資本の情報開示・ISO30414等の基準動向
- リスキリング・学び直しの制度設計や効果測定
- CHRO・人事部門の役割変革に関する提言
- 「両効きの経営」における人材投資のあり方

■ 除外すべき記事（厳格に除外）:
- 労働安全衛生・労災・安全規則に関する法令改正
- 障害者雇用の法的義務対応（DEI戦略としての議論は可）
- 最低賃金・残業規制など労務管理の実務的な法改正
- 単なるイベント告知・セミナー案内・書籍紹介
- 個別企業のPR記事・プレスリリースの転載
- 採用情報・求人に関する記事
- 人的資本経営と直接関係のない一般的なビジネスニュース

{articles_text}

以下のJSON配列で返してください（他の文字列は一切不要）:
[
  {{
    "index": 記事番号,
    "category": "deep|explore|policy|tech",
    "title_edit": "編集部視点で簡潔に改善。出典名やサイト名は削除。不要ならnull",
    "summary": "80文字以内。経営層が30秒で要点を掴める要約。数字や固有名詞を含めて具体的に。"
  }}
]

カテゴリ判定基準:
- policy: 人的資本開示基準・ISO30414・伊藤レポート等の政策動向
- deep（知の深化）: 既存事業の人材最適化、リーダーシップ開発、エンゲージメント、研修・評価制度
- explore（知の探索）: 新規事業人材、イノベーション、ゼロイチ人材、価値創造
- tech: タレントマネジメントSaaS、AI人事、ピープルアナリティクス

最大{MAX_ARTICLES}件まで。テーマに合致する質の高い記事がなければ、少数でも構いません。"""
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60,
        )
        data = response.json()
        text = data['content'][0]['text']
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            results = json.loads(json_match.group())
            curated = []
            for r in results:
                idx = r['index'] - 1
                if 0 <= idx < len(articles):
                    a = articles[idx]
                    curated.append({
                        'date': a['date'],
                        'title': r.get('title_edit') or a['title'],
                        'summary': r.get('summary', a['raw_summary'][:80]),
                        'cat': r.get('category', a['hint']),
                        'source': a['source'],
                        'url': a['url'],
                    })
            print(f"  → Claude厳選: {len(curated)}件（候補{len(articles)}件から）")
            return curated
    except Exception as e:
        print(f"  Claude APIエラー: {e}")
    return fallback_classify(articles)


def fallback_classify(articles):
    result = []
    for a in articles[:MAX_ARTICLES]:
        text = f"{a['title']} {a.get('raw_summary','')}"
        if any(kw in text for kw in ['経産省', '金融庁', '開示', '伊藤レポート', 'ガイドライン', 'SSBJ']):
            cat = 'policy'
        elif any(kw in text for kw in ['SaaS', 'AI', 'テック', 'Tech', 'システム', 'データ分析', 'タレマネ']):
            cat = 'tech'
        elif any(kw in text for kw in ['新規事業', 'イノベーション', 'ゼロイチ', '価値創造']):
            cat = 'explore'
        else:
            cat = a.get('hint', 'deep')
        result.append({
            'date': a['date'], 'title': a['title'],
            'summary': a['raw_summary'][:80],
            'cat': cat, 'source': a['source'],
            'url': a.get('url', ''),
                        'url': a['url'],
        })
    return result


def save_json(articles):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "last_updated": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+09:00'),
        "total": len(articles),
        "articles": articles
    }
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding='utf-8'))
            new_titles = {re.sub(r'\s+', '', a['title'])[:30] for a in articles}
            merged = list(articles)
            for a in existing.get('articles', []):
                key = re.sub(r'\s+', '', a['title'])[:30]
                if key not in new_titles:
                    merged.append(a)
            merged = merged[:MAX_ARTICLES]
            output['articles'] = merged
            output['total'] = len(merged)
        except Exception:
            pass
    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\n💾 {len(output['articles'])}件を {OUTPUT_FILE} に保存")


def main():
    print("=" * 60)
    print("HC Landscape — ニュース自動収集 v4（全28ソース体制）")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"対象期間: 過去{DAYS_BACK}日間 / ソース: {len(SOURCES)}件")
    print("=" * 60)
    print(f"\n📡 RSS取得中...")
    candidates = fetch_articles()
    print(f"\n  候補記事: {len(candidates)}件")
    if not candidates:
        print("⚠️ 新しい記事が見つかりませんでした")
        return
    print("\n🤖 Claude APIで厳選・分類・要約中...")
    curated = curate_with_claude(candidates)
    if not curated:
        print("⚠️ 選定基準を満たす記事がありませんでした")
        return
    cats = {}
    for a in curated:
        c = a.get('cat', 'deep')
        cats[c] = cats.get(c, 0) + 1
    cat_names = {'deep': '知の深化', 'explore': '知の探索', 'policy': '政策・開示', 'tech': 'HR Tech'}
    print("\n📊 カテゴリ別:")
    for c, count in sorted(cats.items()):
        print(f"    {cat_names.get(c, c)}: {count}件")
    save_json(curated)
    print("\n✅ 完了！")


if __name__ == "__main__":
    main()
