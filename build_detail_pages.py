"""「くわしい特徴（long_detail）」を持つ項目ごとに、専用の詳細ページ
（detail/{id}.html）を作る（個人用）。

これまではポップアップ表示にしていたが、「ホームページがツリー状に下の階層へ
広がっていく」感覚が欲しいとの依頼があり、ポップアップではなく実際に別ファイル
として詳細ページを作り、一覧ページからそこへ移動するリンクにした。

data.jsonが更新されるたびに、このスクリプトを実行し直せば詳細ページも
最新の内容に作り直される。
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data.json"
DETAIL_DIR = PROJECT_DIR / "detail"

PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} － くわしい特徴</title>
<script>
try {{
  var savedTheme = localStorage.getItem('dqwalk-theme');
  if (savedTheme && savedTheme !== 'default') document.documentElement.setAttribute('data-theme', savedTheme);
}} catch (error) {{}}
</script>
<link rel="stylesheet" href="detail.css">
</head>
<body>
<div class="wrap">
<a class="back" href="../index.html">← 所持チェックの一覧にもどる</a>
<article class="detail-card">
{image_html}
<h1>{name}</h1>
<p class="summary">{summary}</p>
<h2>くわしい特徴</h2>
<p class="long-detail">{long_detail}</p>
</article>
</div>
</body>
</html>
"""


def escape(value):
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_page(item):
    image_html = ""
    if item.get("image_path"):
        image_path = "../" + item["image_path"]
        image_html = f'<img class="detail-image" src="{escape(image_path)}" alt="{escape(item["name"])}">'
    return PAGE_TEMPLATE.format(
        name=escape(item["name"]),
        image_html=image_html,
        summary=escape(item.get("detail", "")),
        long_detail=escape(item.get("long_detail", "")),
    )


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = [item for item in data.get("items", []) if item.get("long_detail")]

    DETAIL_DIR.mkdir(exist_ok=True)
    for item in items:
        page_path = DETAIL_DIR / f"{item['id']}.html"
        page_path.write_text(build_page(item), encoding="utf-8")

    print(f"詳細ページを{len(items)}件作成しました（{DETAIL_DIR}）。")


if __name__ == "__main__":
    main()
