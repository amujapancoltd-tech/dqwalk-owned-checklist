"""武器・防具・こころに共通の「くわしい特徴」（long_detail）取得処理（個人用）。

各項目の個別ページ（GameWith）には、SEO用の構造化データ（JSON-LD）として
記事本文の全文がきれいなJSON形式で埋め込まれている。ここから
「(項目名)の強い点」〜「(項目名)の性能比較」の間の文章だけを抜き出し、
long_detailとしてdata.jsonに保存する。これにより外部リンクを開かなくても、
このサイトの中だけで詳しい特徴を確認できるようにする（sync_weapon_long_detail.py
などの、種類ごとのスクリプトから呼び出して使う）。

サイトへの負担を抑えるため、1件ごとに間隔をあけて取得する。
"""

import json
import re
import time
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
USER_AGENT = "DQWalkPersonalChecklist/1.0"
REQUEST_INTERVAL_SECONDS = 0.6

# 武器・防具向け：GameWithの評価文（強い点・弱い点）は使わず、レベル別スキル一覧
# （事実の数値データ）だけを「くわしい特徴」にする
SKILL_LIST_START_SUFFIX = "の習得スキル"
SKILL_LIST_SUB_HEADING = "レベル別習得スキル"
SKILL_LIST_LIMIT_BREAK_HEADING = "限界突破の習得スキル"
# 武器の記事には、スキル一覧の後ろにGameWithの評価文・性能比較表が続くため、
# それらの見出しが出てきた時点で打ち切る（防具の記事にはこれらの見出し自体が無い）。
SKILL_LIST_END_SUFFIXES = [
    "の評価",
    "の強い点",
    "の性能比較",
    "ドラクエウォークの装備関連記事",
    "の装備関連記事",
    "の関連記事",
    "関連記事",
]
LEVEL_MARKER_PATTERN = re.compile(r"(Lv\d+|\d凸)")

# こころ向け：ランク別特殊効果だけを「くわしい特徴」にする（出現場所・図鑑データは対象外）
HEART_INFO_START_SUFFIX = "の効果とステータス"
HEART_INFO_END_SUFFIXES = ["全モンスターの評価はこちら", "ドラクエウォークの関連記事", "の関連記事"]
HEART_INFO_OUTRO_SUFFIX = "の出現場所と図鑑データ"
# Sランク（こころ最大コスト+4、まれに+5等）の情報だけを残し、+3以下のランクは削除する。
HEART_INFO_RANK_CUTOFF_PATTERN = re.compile(r"こころの?最大コスト\+3")

LD_JSON_PATTERN = re.compile(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', re.S)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def strip_own_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def extract_article_body(html):
    for match in LD_JSON_PATTERN.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        body = payload.get("articleBody")
        if body:
            return body
    return None


def extract_heart_info(article_body, name):
    start = article_body.find(name + HEART_INFO_START_SUFFIX)
    if start == -1:
        return None
    end_candidates = [article_body.find(suffix, start) for suffix in HEART_INFO_END_SUFFIXES]
    end_candidates = [pos for pos in end_candidates if pos != -1]
    end = min(end_candidates) if end_candidates else len(article_body)
    fragment = article_body[start:end].strip()
    # 「出現場所と図鑑データ」以降（出現場所／みかけやすさ／こころの色／系統／
    # 図鑑No．／解説）は表示不要なので、ランク別特殊効果の内容だけを残して切り捨てる。
    outro_start = fragment.find(name + HEART_INFO_OUTRO_SUFFIX)
    if outro_start != -1:
        fragment = fragment[:outro_start]
    # Sランク（こころ最大コスト+4以上）だけ残し、+3以下のランク情報は切り捨てる。
    rank_cutoff = HEART_INFO_RANK_CUTOFF_PATTERN.search(fragment)
    if rank_cutoff:
        fragment = fragment[:rank_cutoff.start()]
    # GameWithの見出し文言（「◯◯の効果とステータス」「ランク別特殊効果」）は使わず、
    # 自分たちの見出しに置き換える。中身の数値・効果名はそのまま（事実データのため）。
    fragment = strip_own_prefix(fragment, name + HEART_INFO_START_SUFFIX)
    fragment = fragment.replace("ランク別特殊効果", "【ランク特殊効果】\n", 1)
    # 「ランク別ステータス」の後ろに続く生の数値の羅列（HP・MPなどの数字が
    # 区切りなく並んだだけで人が読んでも意味が分からない）は、丸ごと取り除く。
    # （行の途中から始まっていても消えるよう、改行の有無は問わない）
    fragment = re.sub(r"ランク別ステータス[^\n]*", "", fragment)
    return fragment.strip()


def extract_skill_list(article_body, name):
    start = article_body.find(name + SKILL_LIST_START_SUFFIX)
    if start == -1:
        return None
    end_candidates = [article_body.find(suffix, start) for suffix in SKILL_LIST_END_SUFFIXES]
    end_candidates = [pos for pos in end_candidates if pos != -1]
    end = min(end_candidates) if end_candidates else len(article_body)
    fragment = article_body[start:end].strip()
    # GameWithの見出し文言（「◯◯の習得スキル」「レベル別習得スキル」「限界突破の習得スキル」）
    # は使わず、自分たちの見出しに置き換える。中身のLv・凸・スキル名・数値はそのまま（事実データのため）。
    fragment = strip_own_prefix(fragment, name + SKILL_LIST_START_SUFFIX)
    fragment = strip_own_prefix(fragment, SKILL_LIST_SUB_HEADING)
    fragment = fragment.replace(SKILL_LIST_LIMIT_BREAK_HEADING, "\n【限界突破スキル】", 1)
    fragment = "【レベル別習得スキル】\n" + fragment
    # 武器の記事は、スキル一覧の直後に品名（次の見出し「◯◯の評価」等の前半部分）が
    # くっついたまま残ることがあるので、末尾に付いていれば取り除く。
    if fragment.endswith(name):
        fragment = fragment[: -len(name)]
    # "Lv10"や"1凸"の手前で改行し、読みやすくする
    return LEVEL_MARKER_PATTERN.sub(r"\n\1", fragment).strip()


EXTRACTORS = {
    "skill_list": extract_skill_list,
    "heart_info": extract_heart_info,
}


def sync_long_detail(item_type, label, mode):
    extractor = EXTRACTORS[mode]

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    targets = [item for item in items if item.get("type") == item_type and item.get("detail_url")]

    updated = 0
    failed = []
    for index, item in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] {item['name']} を取得中...")
        try:
            html = download(item["detail_url"])
            article_body = extract_article_body(html)
            long_detail = extractor(article_body, item["name"]) if article_body else None
            if long_detail:
                item["long_detail"] = long_detail
                updated += 1
            else:
                failed.append(item["name"])
        except Exception as error:
            print(f"  → 取得に失敗: {error}")
            failed.append(item["name"])
        time.sleep(REQUEST_INTERVAL_SECONDS)

    print(f"くわしい特徴を追加できた{label}: {updated}/{len(targets)}件")
    if failed:
        print(f"取得できなかった{label}（{len(failed)}件）:")
        print("、".join(failed))

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("data.json を更新しました。")
