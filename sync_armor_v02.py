"""GameWithの防具一覧を取得し、所持チェック用データに追加する（個人用・v02）。

v01からの変更点：①新しい防具のIDを「今ある最大の番号＋1」にした（v01は「何番目か」で
付けていたため、既存のIDとかぶっていた）。②同じ名前で部位が違う防具（例：黒王の
メタルキング兜の頭・よろい上・よろい下）を別々に扱うため、「名前＋部位」で見分ける。


sync_gamewith.py（武器・こころ）とは別スクリプト。防具はページの見出し
（たて(盾)一覧・あたま(頭)一覧・よろい上一覧・よろい下一覧）ごとに種類が
分かれているため、見出しの区間ごとに表を読み取って種類(category)も一緒に
つける。
"""

import json
import re
import time
from datetime import date
from pathlib import Path

from sync_gamewith import TableParser, download, download_binary, normalize_detail_url
from sync_gamewith_v02 import make_new_id

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
IMAGE_DIR = PROJECT_DIR / "images" / "armors"

ARMOR_PAGE = "https://gamewith.jp/dq-walk/article/show/166330"
ARMOR_CATEGORIES = [
    ("たて(盾)一覧", "盾"),
    ("あたま(頭)一覧", "頭"),
    ("よろい上(鎧上)一覧", "よろい上"),
    ("よろい下(鎧下)一覧", "よろい下"),
]
SECTION_END_MARKER = "ドラクエウォークの関連記事"


def rows_with_media(html_fragment):
    parser = TableParser()
    parser.feed(html_fragment)
    return parser.rows, parser.row_links, parser.row_images


def extract_armor_rows(html):
    positions = []
    for heading_text, category in ARMOR_CATEGORIES:
        pattern = re.compile(r"<h[23][^>]*>\s*" + re.escape(heading_text) + r"\s*</h[23]>")
        match = pattern.search(html)
        if match:
            positions.append((match.start(), category))
    positions.sort()
    last_heading_start = positions[-1][0] if positions else 0
    end_match = re.search(re.escape(SECTION_END_MARKER), html[last_heading_start:])
    section_end = last_heading_start + end_match.start() if end_match else len(html)

    results = []
    seen = set()
    for index, (start, category) in enumerate(positions):
        stop = positions[index + 1][0] if index + 1 < len(positions) else section_end
        fragment = html[start:stop]
        rows, row_links, row_images = rows_with_media(fragment)
        for row_index, row in enumerate(rows):
            if len(row) < 3 or row[0] in {"防具名", "武器", "防具", "アクセ"}:
                continue
            name, score, skill = row[:3]
            name = re.sub(r"\s+", " ", name).strip()
            if not name or not re.search(r"\d", score) or len(name) > 40:
                continue
            key = (category, name)
            if key in seen:
                continue
            seen.add(key)
            detail = f"攻略班 {score}"
            if skill:
                detail += f" / {skill[:150]}"
            results.append({
                "name": name,
                "detail": detail,
                "category": category,
                "link": row_links[row_index] if row_index < len(row_links) else "",
                "image": row_images[row_index] if row_index < len(row_images) else "",
            })
    return results


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    old_by_key = {(item["name"], item.get("category")): item for item in items if item.get("type") == "armor"}
    known_ids = {item["id"] for item in items}
    assigned_ids = set()
    other_items = [item for item in items if item.get("type") != "armor"]

    print("防具ページを取得中...")
    page = download(ARMOR_PAGE)
    armor_rows = extract_armor_rows(page)
    if not armor_rows:
        raise RuntimeError("防具データを取得できませんでした。元データは変更していません。")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    new_armor_items = []
    for entry in armor_rows:
        previous = old_by_key.get((entry["name"], entry["category"]))
        if previous and previous["id"] not in assigned_ids:
            armor_id = previous["id"]
        else:
            armor_id = make_new_id("armor", known_ids | assigned_ids)
        assigned_ids.add(armor_id)
        item = {
            "id": armor_id,
            "name": entry["name"],
            "detail": entry["detail"],
            "type": "armor",
            "category": entry["category"],
            "source_url": ARMOR_PAGE,
        }
        detail_url = normalize_detail_url(entry["link"]) or (previous.get("detail_url") if previous else "") or ARMOR_PAGE
        item["detail_url"] = detail_url
        if entry["image"]:
            image_path = IMAGE_DIR / f"{item['id']}.png"
            try:
                if not image_path.exists():
                    download_binary(entry["image"], image_path)
                    time.sleep(0.2)
                item["image_path"] = f"images/armors/{item['id']}.png"
            except Exception as error:
                print(f"画像を取得できませんでした: {item['name']} ({error})")
        elif previous and previous.get("image_path"):
            item["image_path"] = previous["image_path"]
        if previous and previous.get("long_detail"):
            item["long_detail"] = previous["long_detail"]
        new_armor_items.append(item)

    data["items"] = other_items + new_armor_items
    data["updated_at"] = str(date.today())
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"防具: {len(new_armor_items)}件を取り込みました。")
    for heading_text, category in ARMOR_CATEGORIES:
        count = sum(1 for item in new_armor_items if item["category"] == category)
        print(f"  {category}: {count}件")
    print("data.json を更新しました。")


if __name__ == "__main__":
    main()
