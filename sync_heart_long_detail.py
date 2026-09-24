from long_detail_common import sync_long_detail

if __name__ == "__main__":
    # こころには評価文が無いため、ランク別効果・出現場所・図鑑データを
    # 「くわしい特徴」として取り込む
    sync_long_detail("heart", "こころ", mode="heart_info")
