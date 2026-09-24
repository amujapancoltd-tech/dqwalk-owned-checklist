"""武器の「くわしい特徴」（long_detail）を取得する（個人用）。取得処理の中身は
long_detail_common.pyにまとめてある（防具・こころも同じ仕組みで取得する）。
"""

from long_detail_common import sync_long_detail

if __name__ == "__main__":
    # GameWithの評価文（強い点・弱い点）は使わず、レベル別スキル一覧（事実の数値データ）を
    # 「くわしい特徴」として取り込む（防具と同じ仕組み）
    sync_long_detail("weapon", "武器", mode="skill_list")
