"""武器・防具・こころ・職業のデータを、まとめて最新の状態に更新する（個人用・v02）。

実行順序が大事なため、以下の順番で1つずつ呼び出す。
1. sync_gamewith_v02.py  … 武器・こころの基本データ（GameWithの一覧ページから）
2. sync_armor_v02.py     … 防具の基本データ
3. sync_categories.py … 武器の種類・こころの色
4. sync_keito.py      … こころの系統（game8のモンスター図鑑から）
5. sync_heart_cost.py … こころのコスト（こころ編成シミュレーション用）
6. sync_jobs.py       … 職業データ（jobs.json、armor/heart/weaponとは別ファイル）
7. sync_new_long_detail_v02.py … 新しい防具の「くわしい特徴」と個別ページ（detail/）

途中でどれか1つが失敗しても、残りは続けて実行し、最後にまとめて結果を表示する。
"""

import traceback

STEPS = [
    ("武器・こころ（基本データ）", "sync_gamewith_v02"),
    ("防具（基本データ）", "sync_armor_v02"),
    ("武器の種類・こころの色", "sync_categories"),
    ("こころの系統", "sync_keito"),
    ("こころのコスト", "sync_heart_cost"),
    ("職業データ", "sync_jobs"),
    ("新しい防具のくわしい特徴・個別ページ", "sync_new_long_detail_v02"),
]


def main():
    results = []
    for label, module_name in STEPS:
        print(f"\n=== {label}（{module_name}.py）を更新中 ===")
        try:
            module = __import__(module_name)
            module.main()
            results.append((label, "OK", ""))
        except Exception as error:
            print(f"エラーが発生しました: {error}")
            traceback.print_exc()
            results.append((label, "失敗", str(error)))

    print("\n=== 更新結果まとめ ===")
    for label, status, message in results:
        line = f"{status}：{label}"
        if message:
            line += f"（{message}）"
        print(line)

    if any(status == "失敗" for _, status, _ in results):
        print("\n一部の更新に失敗しました。上のエラー内容を確認してください。成功した分のデータは反映されています。")
    else:
        print("\nすべて更新できました。")


if __name__ == "__main__":
    main()
