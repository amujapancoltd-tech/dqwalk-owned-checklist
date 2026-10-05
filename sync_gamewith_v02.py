"""GameWithの武器・こころ一覧を取得し、所持チェック用データを更新する（v02）。

v01からの変更点：新しい項目に付けるIDを「その種類の今ある最大の番号＋1」にした。
v01は「何番目か」で付けていたため、既存のIDとかぶることがあった（かぶると
所持チェックの印が別の項目にもついてしまう）。また、v01は「くわしい特徴（long_detail）」を
消してしまっていたため、v02では引き継ぐ。
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
IMAGE_DIRS = {
    "weapon": PROJECT_DIR / "images" / "weapons",
    "heart": PROJECT_DIR / "images" / "hearts",
}
USER_AGENT = "DQWalkPersonalChecklist/1.0"
SOURCES = {
    "weapon": "https://gamewith.jp/dq-walk/article/show/166329",
    "heart": "https://gamewith.jp/dq-walk/article/show/166401",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row_links = []
        self.row_images = []
        self.row = None
        self.cell_text = None
        self.cell_link = None
        self.cell_image = None
        self.cell_tag = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
            self.row_links.append("")
            self.row_images.append("")
        elif tag in {"td", "th"} and self.row is not None:
            self.cell_text = []
            self.cell_tag = tag
        elif tag == "a" and self.cell_text is not None:
            self.cell_link = dict(attrs).get("href", "")
        elif tag == "img" and self.cell_text is not None and not self.cell_image:
            attributes = dict(attrs)
            self.cell_image = attributes.get("data-original") or attributes.get("src", "")

    def handle_data(self, data):
        if self.cell_text is not None:
            self.cell_text.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell_text is not None:
            text = " ".join("".join(self.cell_text).split())
            self.row.append(text)
            if len(self.row) == 1:
                self.row_links[-1] = self.cell_link or ""
                self.row_images[-1] = self.cell_image or ""
            self.cell_text = None
            self.cell_tag = None
            self.cell_link = None
            self.cell_image = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def download_binary(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def unique_items(page, item_type):
    parser = TableParser()
    parser.feed(page)
    items = []
    seen = set()
    for row_index, row in enumerate(parser.rows):
        if item_type == "weapon":
            if len(row) < 4 or row[0] in {"武器", "防具", "アクセ"}:
                continue
            name, score, user_score, skill = row[:4]
            if not re.search(r"\d", score) or len(name) > 40:
                continue
            detail = f"攻略班 {score}"
            if skill:
                detail += f" / {skill[:150]}"
        else:
            if len(row) < 3 or row[0] in {"モンスター", "こころ"}:
                continue
            name, effect, score = row[:3]
            if len(name) > 40 or name in {"赤", "青", "黄", "紫", "緑", "黒", "白", "虹"}:
                continue
            if "こころなし" in effect:
                # モンスターは掲載されているが、こころ自体は存在しない（コラボ等の一部モンスター）
                continue
            # 追加されたばかりのボスのこころは、攻略班の点数がまだ空欄のことがある
            # （例：黒き偽竜グレイナル）。点数が無くても取りこぼさないようにする。
            detail = f"{effect[:180]} / {score}点" if re.search(r"\d", score) else f"{effect[:180]} / 評価未定"
        name = re.sub(r"\s+", " ", name).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        item = {"name": name, "detail": detail, "type": item_type}
        if parser.row_links[row_index]:
            item["detail_url"] = parser.row_links[row_index]
        if parser.row_images[row_index]:
            item["image_url"] = parser.row_images[row_index]
        items.append(item)
    return items


def normalize_detail_url(value):
    if not value:
        return ""
    url = value.strip()
    if re.match(r"^https?://gamewith\.jp/dq-walk/article/show/\d+/?$", url, re.I):
        return url.rstrip("/")
    return ""


def make_new_id(item_type, used_ids):
    """その種類の、数字つきIDの最大番号＋1で、新しいIDを作る。"""
    numbers = [int(value.split("-", 1)[1]) for value in used_ids
               if value.startswith(item_type + "-") and value.split("-", 1)[1].isdigit()]
    return f"{item_type}-{(max(numbers) + 1 if numbers else 0):04d}"


def main():
    old_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    old_by_name = {(item["type"], item["name"]): item for item in old_data.get("items", [])}
    # 防具など、このスクリプトが扱わない種類のデータはそのまま残す。
    new_items = [item for item in old_data.get("items", []) if item["type"] not in SOURCES]
    known_ids = {item["id"] for item in old_data.get("items", [])}
    assigned_ids = set()
    requested_types = {"weapon"} if "--weapon" in sys.argv[1:] else set(SOURCES)
    for item_type, url in SOURCES.items():
        if item_type not in requested_types:
            new_items.extend(item for item in old_data.get("items", []) if item["type"] == item_type)
            continue
        page = download(url)
        for item in unique_items(page, item_type):
            previous = old_by_name.get((item_type, item["name"]))
            if previous and previous["id"] not in assigned_ids:
                item["id"] = previous["id"]
            else:
                item["id"] = make_new_id(item_type, known_ids | assigned_ids)
            assigned_ids.add(item["id"])
            item["source_url"] = url
            normalized_item_url = normalize_detail_url(item.get("detail_url"))
            item["detail_url"] = normalized_item_url or url
            if previous and previous.get("long_detail"):
                # 「くわしい特徴」は別のスクリプトで取得するため、消さずに引き継ぐ
                item["long_detail"] = previous["long_detail"]
            if previous:
                previous_url = normalize_detail_url(previous.get("detail_url"))
                if previous_url:
                    item["detail_url"] = previous_url
            if item.get("image_url"):
                image_dir = IMAGE_DIRS.get(item_type, IMAGE_DIRS["weapon"])
                image_dir.mkdir(parents=True, exist_ok=True)
                image_path = image_dir / f"{item['id']}.png"
                try:
                    if not image_path.exists():
                        download_binary(item["image_url"], image_path)
                        time.sleep(0.2)
                    item["image_path"] = f"images/{item_type}s/{item['id']}.png"
                except Exception as error:
                    print(f"画像を取得できませんでした: {item['name']} ({error})")
            new_items.append(item)
    if not new_items:
        raise RuntimeError("一覧データを取得できませんでした。元データは変更していません。")
    new_data = {
        "updated_at": str(date.today()),
        "source": "GameWith（個人用の参照データ）",
        "items": new_items,
    }
    DATA_FILE.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"更新完了: {DATA_FILE}")
    print(f"武器: {sum(item['type'] == 'weapon' for item in new_items)}件")
    print(f"こころ: {sum(item['type'] == 'heart' for item in new_items)}件")
    print(f"更新日: {new_data['updated_at']}")


if __name__ == "__main__":
    main()
