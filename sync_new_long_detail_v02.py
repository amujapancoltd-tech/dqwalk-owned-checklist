"""「くわしい特徴」がまだ無い武器・防具・こころだけを取得し、個別ページ（detail/）も作り直す（個人用）。

sync_armor_long_detail.pyなどは全件（約1,000件ずつ）を取得し直すため時間がかかる。
こちらは、新しく増えた項目など「くわしい特徴」が空の項目だけを取得する。
取得できない項目（GameWith側に記載が無いもの）は、毎回スキップされる。
"""

import json
import time

import build_detail_pages
import long_detail_common as common


def main():
    data = json.loads(common.DATA_FILE.read_text(encoding="utf-8"))
    modes = {"weapon": "skill_list", "armor": "skill_list", "heart": "heart_info"}
    targets = [item for item in data["items"]
               if item.get("type") in modes and item.get("detail_url") and not item.get("long_detail")]
    added, failed = 0, []
    for index, item in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] {item['name']} を取得中...")
        try:
            body = common.extract_article_body(common.download(item["detail_url"]))
            text = common.EXTRACTORS[modes[item["type"]]](body, item["name"]) if body else None
        except Exception as error:
            print(f"  → 取得に失敗: {error}")
            text = None
        if text:
            item["long_detail"] = text
            added += 1
        else:
            failed.append(item["name"])
        time.sleep(common.REQUEST_INTERVAL_SECONDS)
    common.DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"くわしい特徴を追加できた項目: {added}/{len(targets)}件（取得できず{len(failed)}件）")
    build_detail_pages.main()


if __name__ == "__main__":
    main()
