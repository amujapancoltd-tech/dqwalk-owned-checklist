"""こころの「コスト」（職業のこころ枠に入れる時に消費する数値）を、
GameWithの色別ページから取得してdata.jsonに追加する（個人用）。

sync_categories.py（色の取得）とは別スクリプト。同じ色別ページの、
こころ名・コスト・HP・MPなど12列のステータス表を読み取り、名前が
一致したこころにだけ'cost'を追加する。
"""

import json
import re
import time
from pathlib import Path

from sync_categories import HEART_COLOR_PAGES
from sync_gamewith import TableParser, download

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"


def extract_heart_costs(html):
    parser = TableParser()
    parser.feed(html)
    costs = {}
    for row in parser.rows:
        if len(row) != 12 or row[0] in {"こころ", ""}:
            continue
        name = re.sub(r"\s+", " ", row[0]).strip()
        cost_text = row[1].strip()
        if name and re.fullmatch(r"\d+", cost_text):
            costs[name] = int(cost_text)
    return costs


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])

    all_costs = {}
    for color, url in HEART_COLOR_PAGES.items():
        print(f"こころページを取得中: {color}")
        html = download(url)
        all_costs.update(extract_heart_costs(html))
        time.sleep(0.3)

    matched = 0
    hearts = [item for item in items if item.get("type") == "heart"]
    for item in hearts:
        cost = all_costs.get(item["name"])
        if cost is not None:
            item["cost"] = cost
            matched += 1
    print(f"こころ: {matched}/{len(hearts)}件にコストを追加できました。")

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("data.json を更新しました。")


if __name__ == "__main__":
    main()
