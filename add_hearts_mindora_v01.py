"""GameWithの一覧に載っていない新しいこころを、みんドラ（9db.jp）のデータから data.json に足す（個人用）。

使い方（足したいこころの、みんドラ上の番号を渡す）:
  ..\\.venv\\Scripts\\python.exe add_hearts_mindora_v01.py 20411 20460 20136 20139

- すでに同じ名前のこころがあれば、足さずにスキップする（二重登録しない）。
- 既存の項目のIDは変えない。新しい項目だけ、いちばん大きい番号の次から付ける。
- 足したあと、画像の保存と個別ページ（detail/）の作り直しまで行う。
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

import build_detail_pages

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
IMAGE_DIR = PROJECT_DIR / "images" / "hearts"
USER_AGENT = "Mozilla/5.0 (DQWalkPersonalChecklist/1.0)"
MINDORA_PAGE_URL = "https://9db.jp/dqwalk/data/33"
DATA_URL_PATTERN = re.compile(r'src="(https://cdn08\.net/dqwalk/data/\d+\?ver=\d+)"')
JS_PATTERN = re.compile(r"JSON\.parse\('(.*)'\)", re.S)

LINE_TO_KEITO = {
    "スライム": "スライム系", "鳥": "鳥系", "虫": "虫系", "植物": "植物系", "物質": "物質系",
    "エレメント": "エレメント系", "水": "水系", "けもの": "獣系", "悪魔": "悪魔系",
    "マシン": "マシン系", "ゾンビ": "ゾンビ系", "怪人": "怪人系", "ドラゴン": "ドラゴン系",
    "？？？？": "????系",
}


def fetch(url, binary=False):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    return body if binary else body.decode("utf-8", "ignore")


def load_mindora_hearts():
    page = fetch(MINDORA_PAGE_URL)
    for url in DATA_URL_PATTERN.findall(page):
        script = fetch(url)
        match = JS_PATTERN.search(script)
        if match:
            payload = json.loads(match.group(1).replace("\\'", "'"))
            if "kokoro" in payload:
                return payload["kokoro"]
    raise RuntimeError("みんドラのこころデータが見つかりませんでした")


def main(ids):
    kokoro = load_mindora_hearts()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data["items"]
    names = {item["name"] for item in items if item["type"] == "heart"}
    numbers = [int(match.group(1)) for item in items
               if (match := re.fullmatch(r"heart-(\d+)", item["id"]))]
    next_number = max(numbers) + 1
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for mindora_id in ids:
        record = kokoro.get(f"k{mindora_id}")
        if not record:
            print(f"みんドラに番号 {mindora_id} が見つかりません。スキップ")
            continue
        name = record["name"]
        if name in names:
            print(f"{name}：すでにあるのでスキップ")
            continue
        item_id = f"heart-{next_number:04d}"
        next_number += 1
        skills = [text.replace("％", "%") for text in record.get("skill", [])]
        effect = "".join(skills)
        image_url = f"https://cdn08.net/dqwalk/data/img20/img{mindora_id}_2.jpg"
        image_name = f"{item_id}.jpg"
        (IMAGE_DIR / image_name).write_bytes(fetch(image_url, binary=True))
        items.append({
            "name": name,
            "detail": effect,
            "type": "heart",
            "detail_url": f"https://9db.jp/dqwalk/data/{mindora_id}",
            "image_url": image_url,
            "id": item_id,
            "source_url": MINDORA_PAGE_URL,
            "long_detail": "【ランク特殊効果】\n" + effect,
            "image_path": f"images/hearts/{image_name}",
            "color": [record["color"]],
            "keito": [LINE_TO_KEITO.get(record.get("line"), "その他/特別")],
            "cost": record["cost"],
        })
        names.add(name)
        print(f"追加：{name}（{item_id}）")

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    build_detail_pages.main()


if __name__ == "__main__":
    main(sys.argv[1:])
