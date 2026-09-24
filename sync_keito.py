"""こころの系統（スライム系・物質系など）を、みんドラ（9db.jp）とgame8の
2つのサイトを参照して、data.jsonに追記する（個人用）。

もともとはgame8のモンスター図鑑ページ（系統ごとに14ページ）だけを見ていたが、
game8側のページ更新が追いついておらず新しいこころ（魔王ウルノーガなど）が
拾えないケースがあった。みんドラのこころ検索ページ（例:
https://9db.jp/dqwalk/data/33 ）は、表示用のJavaScriptに埋め込まれた
JSONの中に全こころの系統（line）情報を持っていて、より新しいこころにも
対応できている。ただしみんドラ側にも系統が空のこころがあるため、
①まずみんドラのデータを見る → ②みんドラに無ければgame8のページも見る、
の順で両方を組み合わせて、なるべく多くのこころに系統を付ける。

名前が一致したこころにだけ 'keito' を追加し、どちらにも見つからなかった
ものは「その他/特別」として扱う（プレイアブルキャラ本人・コラボキャラなど、
そもそも系統を持たないもの）。
"""

import json
import re
import time
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
USER_AGENT = "Mozilla/5.0 (DQWalkPersonalChecklist/1.0)"

# みんドラの「こころ検索」ページが読み込んでいるデータ本体（JS変数 dq）
MINDORA_PAGE_URL = "https://9db.jp/dqwalk/data/33"
MINDORA_DATA_URL_PATTERN = re.compile(r'src="(https://cdn08\.net/dqwalk/data/\d+\?ver=\d+)"')

# みんドラの line（系統）表記 → このツールでの系統名
LINE_TO_KEITO = {
    "スライム": "スライム系",
    "鳥": "鳥系",
    "虫": "虫系",
    "植物": "植物系",
    "物質": "物質系",
    "エレメント": "エレメント系",
    "水": "水系",
    "けもの": "獣系",
    "悪魔": "悪魔系",
    "マシン": "マシン系",
    "ゾンビ": "ゾンビ系",
    "怪人": "怪人系",
    "ドラゴン": "ドラゴン系",
    "？？？？": "????系",
}

GAME8_KEITO_PAGES = {
    "スライム系": "https://game8.jp/dqwalk/708815",
    "鳥系": "https://game8.jp/dqwalk/708816",
    "虫系": "https://game8.jp/dqwalk/708817",
    "植物系": "https://game8.jp/dqwalk/708813",
    "物質系": "https://game8.jp/dqwalk/708818",
    "エレメント系": "https://game8.jp/dqwalk/708819",
    "水系": "https://game8.jp/dqwalk/708820",
    "獣系": "https://game8.jp/dqwalk/708821",
    "悪魔系": "https://game8.jp/dqwalk/708822",
    "マシン系": "https://game8.jp/dqwalk/708823",
    "ゾンビ系": "https://game8.jp/dqwalk/708824",
    "怪人系": "https://game8.jp/dqwalk/708825",
    "ドラゴン系": "https://game8.jp/dqwalk/708826",
    "????系": "https://game8.jp/dqwalk/708827",
}

# data.json側のこころ名 → みんドラ/game8側の名前
# （進化前・イベント限定などで名前の前後に付く言葉が省略され、完全一致しないもの）
NAME_ALIASES = {
    "フラーガ": "神槍兵フラーガ",
    "バゴス": "神狼兵バゴス",
    "アネモーズ": "神威兵アネモーズ",
    "ラプソーン(覚醒)": "暗黒神ラプソーン(覚醒)",
    "オルゴ・デミーラ": "オルゴ・デミーラ(強敵)",
}

GAME8_LIST_START = re.compile(r'id="hl_2"')
GAME8_LIST_END = re.compile(r'id="hl_3"')
GAME8_NAME_PATTERN = re.compile(r'alt="([^"]+?)画像"')

# 「????系」ページだけ見出し番号がひとつずれており、一覧が hl_1〜hl_2 の間にある
GAME8_LIST_BOUNDS = {
    "????系": (re.compile(r'id="hl_1"'), re.compile(r'id="hl_2"')),
}


def download(url, referer=None):
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def fetch_from_mindora():
    page_html = download(MINDORA_PAGE_URL)
    data_urls = MINDORA_DATA_URL_PATTERN.findall(page_html)

    monster_to_keito = {}
    for data_url in data_urls:
        js = download(data_url, referer=MINDORA_PAGE_URL)
        match = re.search(r"var dq = JSON\.parse\('(.*)'\);", js, re.S)
        if not match:
            continue
        json_text = match.group(1).replace("\\'", "'")
        dq = json.loads(json_text)
        kokoro = dq.get("kokoro")
        if not kokoro:
            continue
        for entry in kokoro.values():
            keito = LINE_TO_KEITO.get(entry.get("line"))
            if keito:
                monster_to_keito.setdefault(entry["name"], set()).add(keito)
    return monster_to_keito


def fetch_from_game8():
    monster_to_keito = {}
    for keito, url in GAME8_KEITO_PAGES.items():
        html = download(url)
        start_pattern, end_pattern = GAME8_LIST_BOUNDS.get(keito, (GAME8_LIST_START, GAME8_LIST_END))
        start_match = start_pattern.search(html)
        end_match = end_pattern.search(html)
        if start_match and end_match:
            fragment = html[start_match.end():end_match.start()]
            for name in GAME8_NAME_PATTERN.findall(fragment):
                monster_to_keito.setdefault(name, set()).add(keito)
        time.sleep(0.3)
    return monster_to_keito


def fetch_monster_to_keito():
    print("みんドラからこころの系統データを取得中...")
    monster_to_keito = fetch_from_mindora()

    print("game8からもこころの系統データを取得中（みんドラに無いものを補完）...")
    for name, keitos in fetch_from_game8().items():
        if name not in monster_to_keito:
            monster_to_keito[name] = keitos

    return monster_to_keito


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])

    monster_to_keito = fetch_monster_to_keito()

    hearts = [item for item in items if item.get("type") == "heart"]
    matched = 0
    unmatched = []
    multi_keito = []
    for item in hearts:
        lookup_name = NAME_ALIASES.get(item["name"], item["name"])
        keitos = monster_to_keito.get(lookup_name)
        if keitos:
            item["keito"] = sorted(keitos)
            matched += 1
            if len(keitos) > 1:
                multi_keito.append(item["name"])
        else:
            item["keito"] = ["その他/特別"]
            unmatched.append(item["name"])

    if multi_keito:
        print(f"複数の系統に載っていたこころ（両方の系統タブに表示されます）: {', '.join(multi_keito)}")
    print(f"こころ: {matched}/{len(hearts)}件に系統を追加できました。")
    if unmatched:
        print(f"系統が見つからなかったこころ（{len(unmatched)}件）:")
        print("、".join(unmatched))

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("data.json を更新しました。")


if __name__ == "__main__":
    main()
