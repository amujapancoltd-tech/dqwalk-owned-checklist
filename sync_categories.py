"""武器の種類（片手剣・大剣など）と、こころの色（赤・青など）を
GameWithのページから取得して、data.jsonに追記する（個人用）。

既存のsync_gamewith.pyとは別スクリプト。名前が一致した項目にだけ
'category'（武器）または'color'（こころ）を追加する。一致しなかった
項目は変更しない。
"""

import json
import re
import time
import urllib.request
from pathlib import Path

from sync_gamewith import TableParser

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
USER_AGENT = "DQWalkPersonalChecklist/1.0"

WEAPON_PAGE = "https://gamewith.jp/dq-walk/article/show/166329"
WEAPON_CATEGORIES = [
    ("片手剣一覧", "片手剣"),
    ("オノ(斧)一覧", "オノ"),
    ("短剣一覧", "短剣"),
    ("杖一覧", "杖"),
    ("こん(棍)一覧", "こん"),
    ("ヤリ(槍)一覧", "ヤリ"),
    ("ツメ(爪)一覧", "ツメ"),
    ("ムチ(鞭)一覧", "ムチ"),
    ("ブーメラン一覧", "ブーメラン"),
    ("両手剣一覧", "両手剣"),
    ("EX一覧", "EX"),
]
WEAPON_SECTION_END_MARKER = "ドラクエウォークの関連記事"

HEART_COLOR_PAGES = {
    "赤": "https://gamewith.jp/dq-walk/article/show/168106",
    "青": "https://gamewith.jp/dq-walk/article/show/168107",
    "黄": "https://gamewith.jp/dq-walk/article/show/168108",
    "紫": "https://gamewith.jp/dq-walk/article/show/168110",
    "緑": "https://gamewith.jp/dq-walk/article/show/168109",
    "黒": "https://gamewith.jp/dq-walk/article/show/444057",
    "白": "https://gamewith.jp/dq-walk/article/show/537844",
    "虹": "https://gamewith.jp/dq-walk/article/show/481704",
}


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def rows_in_html(html_fragment):
    parser = TableParser()
    parser.feed(html_fragment)
    return parser.rows


def extract_weapon_categories(html):
    name_to_category = {}
    positions = []
    for heading_text, category in WEAPON_CATEGORIES:
        pattern = re.compile(r"<h[23][^>]*>\s*" + re.escape(heading_text) + r"\s*</h[23]>")
        match = pattern.search(html)
        if match:
            positions.append((match.start(), category))
    positions.sort()
    last_heading_start = positions[-1][0] if positions else 0
    end_match = re.search(re.escape(WEAPON_SECTION_END_MARKER), html[last_heading_start:])
    section_end = last_heading_start + end_match.start() if end_match else len(html)
    for index, (start, category) in enumerate(positions):
        stop = positions[index + 1][0] if index + 1 < len(positions) else section_end
        fragment = html[start:stop]
        for row in rows_in_html(fragment):
            if not row:
                continue
            name = re.sub(r"\s+", " ", row[0]).strip()
            if not name or name in {"武器", "防具", "アクセ"}:
                continue
            name_to_category.setdefault(name, category)
    return name_to_category


def extract_heart_names(html):
    """色別ページは2種類の表組みが混在する（赤/青/黄/紫/緑/白は12列の数値表、
    黒/虹は2列の「こころ名・特殊効果」表）。ページ上部のナビや関連記事欄など
    表以外の2列テキストを拾わないよう、特殊効果欄に必ず含まれる'%'の有無で
    本物のこころ行だけに絞り込む。"""
    names = []
    for row in rows_in_html(html):
        if not row:
            continue
        name = re.sub(r"\s+", " ", row[0]).strip()
        if not name:
            continue
        if len(row) == 12 and name != "こころ":
            names.append(name)
        elif len(row) == 2 and "%" in (row[1] or ""):
            names.append(name)
    return names


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])

    print("武器ページを取得中...")
    weapon_html = download(WEAPON_PAGE)
    weapon_categories = extract_weapon_categories(weapon_html)
    weapon_matched = 0
    for item in items:
        if item.get("type") == "weapon":
            category = weapon_categories.get(item["name"])
            if category:
                item["category"] = category
                weapon_matched += 1
    print(f"武器: {weapon_matched}/{sum(i['type']=='weapon' for i in items)}件に種類を追加できました。")

    heart_colors = {}
    for color, url in HEART_COLOR_PAGES.items():
        print(f"こころページを取得中: {color}")
        html = download(url)
        for name in extract_heart_names(html):
            heart_colors.setdefault(name, set()).add(color)
        time.sleep(0.3)
    heart_matched = 0
    multi_color = []
    for item in items:
        if item.get("type") == "heart":
            colors = heart_colors.get(item["name"])
            if colors:
                item["color"] = sorted(colors)
                heart_matched += 1
                if len(colors) > 1:
                    multi_color.append(item["name"])
    if multi_color:
        print(f"複数の色ページに載っていたこころ（両方の色タブに表示されます）: {', '.join(multi_color)}")
    print(f"こころ: {heart_matched}/{sum(i['type']=='heart' for i in items)}件に色を追加できました。")

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("data.json を更新しました。")


if __name__ == "__main__":
    main()
