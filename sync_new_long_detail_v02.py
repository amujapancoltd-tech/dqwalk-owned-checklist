"""「くわしい特徴」がまだ無い防具だけを取得し、個別ページ（detail/）も作り直す（個人用）。

sync_armor_long_detail.pyは防具ぜんぶ（約1,000件）を取得し直すため時間がかかる。
こちらは、新しく増えた防具など「くわしい特徴」が空の防具だけを取得する。
取得できない防具（GameWith側に習得スキルの記載が無いもの）は、毎回スキップされる。
"""

import json
import time

import build_detail_pages
import long_detail_common as common


def main():
    data = json.loads(common.DATA_FILE.read_text(encoding="utf-8"))
    targets = [item for item in data["items"]
               if item.get("type") == "armor" and item.get("detail_url") and not item.get("long_detail")]
    added, failed = 0, []
    for index, item in enumerate(targets, start=1):
        print(f"[{index}/{len(targets)}] {item['name']} を取得中...")
        try:
            body = common.extract_article_body(common.download(item["detail_url"]))
            text = common.extract_skill_list(body, item["name"]) if body else None
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
    print(f"くわしい特徴を追加できた防具: {added}/{len(targets)}件（取得できず{len(failed)}件）")
    build_detail_pages.main()


if __name__ == "__main__":
    main()
