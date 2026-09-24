"""防具の「くわしい特徴」（long_detail）を取得する（個人用）。取得処理の中身は
long_detail_common.pyにまとめてある（武器・こころも同じ仕組みで取得する）。
"""

from long_detail_common import sync_long_detail

if __name__ == "__main__":
    # 防具にはGameWithの評価文（強い点/弱い点）が無いため、代わりに
    # レベル別スキル一覧を「くわしい特徴」として取り込む
    sync_long_detail("armor", "防具", mode="skill_list")
