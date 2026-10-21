"""武器の画像を、みんドラ（9db.jp）の画像に差し替える（個人用）。

GameWithの画像は番号がずれて別の武器の絵になっているものがあったため
（祖竜【理】の銃剣・魔王の剣など）、名前が一致する武器をみんドラの画像にそろえる。
古い画像ファイル(.png)は消さずに残す。名前が一致しない・取得できない武器は何もしない。
"""

import json
import re
import time
import urllib.request
from pathlib import Path

import build_detail_pages_v02

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
UA = {"User-Agent": "Mozilla/5.0 (DQWalkPersonalChecklist/1.0)"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    page = fetch("https://9db.jp/dqwalk/data/33").decode("utf-8", "ignore")
    weapons = None
    for url in re.findall(r'src="(https://cdn08\.net/dqwalk/data/\d+\?ver=\d+)"', page):
        m = re.search(r"JSON\.parse\('(.*)'\)", fetch(url).decode("utf-8"), re.S)
        if m:
            payload = json.loads(m.group(1).replace("\'", "'"))
            if "weapon" in payload:
                weapons = payload["weapon"]
                break
    by_name = {w["name"]: w for w in weapons.values()}
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    done = skipped = 0
    for item in data["items"]:
        if item["type"] != "weapon":
            continue
        w = by_name.get(item["name"])
        if not w:
            skipped += 1
            continue
        url = f"https://cdn08.net/dqwalk/data/img{w['id'] // 1000}/img{w['id']}_1.jpg"
        try:
            body = fetch(url)
        except Exception as error:
            print(f"取得失敗 {item['name']}: {error}")
            skipped += 1
            continue
        (PROJECT_DIR / "images" / "weapons" / f"{item['id']}.jpg").write_bytes(body)
        item["image_path"] = f"images/weapons/{item['id']}.jpg"
        item["image_url"] = url
        done += 1
        time.sleep(0.3)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"差し替え {done}件／そのまま {skipped}件")
    build_detail_pages_v02.main()


if __name__ == "__main__":
    main()
