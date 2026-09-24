"""GameWithの職業一覧ページから、各職業のアイコン画像・得意武器・こころ枠を取得し、
jobs.jsonを作る（個人用）。

固有特性・ウォーカーズスキル・基本職の総合評価などの説明文は、GameWithの複数ページ
（職業一覧ページ＋各職業の個別ページ）を人間が読んで書き起こしたもの（JOB_DETAILSに
直接記載）。ページによっては説明文がJavaScriptで後から描画され、機械的に正確な形で
取得できなかったため、この部分だけは手作業でまとめている。得意武器・こころ枠・
アイコン画像は毎回このスクリプトで再取得できる。
"""

import json
import re
import time
from pathlib import Path

from sync_gamewith import TableParser, download, download_binary

PROJECT_DIR = Path(__file__).parent
JOBS_FILE = PROJECT_DIR / "jobs.json"
IMAGE_DIR = PROJECT_DIR / "images" / "jobs"

OVERVIEW_PAGE = "https://gamewith.jp/dq-walk/article/show/166174"
TSURIBITO_ICON = "https://img.gamewith.jp/article_tools/dq-walk/gacha/tsuribito_i.png"
TSURIBITO_LINK = "https://gamewith.jp/dq-walk/article/show/576149"
HEART_COLOR_ICON_DIR = PROJECT_DIR / "images" / "heart_colors"
HEART_COLOR_ICONS = {
    "虹": "rainbow_si", "赤": "red_si", "青": "blue_si", "黄": "yellow_si",
    "緑": "green_si", "紫": "purple_si", "黒": "black_si", "白": "white_si",
    "赤・黄": "red_yellow_si", "黄・紫": "yellow_purple_si", "青・緑": "blue_green_si",
    "黄・青": "yellow_blue_si", "赤・紫": "red_purple_si", "黄・緑": "yellow_green_si",
    "青・紫": "blue_purple_si", "赤・黒": "red_black_si", "赤・白": "red_white_si",
    "青・白": "blue_white_si", "黄・黒": "yellow_black_si", "紫・緑": "purple_green_si",
    "赤・青": "red_blue_si",
}
HEART_COLOR_ICON_BASE = "https://img.gamewith.jp/article_tools/dq-walk/gacha/"

WEAPON_NAMES = ["両手剣", "片手剣", "ブーメラン", "こん", "オノ", "短剣", "杖", "ヤリ", "ツメ", "ムチ", "EX"]
WEAPON_PATTERN = re.compile("|".join(re.escape(name) for name in WEAPON_NAMES))
HEART_SLOT_PATTERN = re.compile(r"[赤青黄緑紫黒白虹](?:・[赤青黄緑紫黒白])?")

# 手作業でGameWithの各職業ページ（固有特性・総合評価など）から書き起こした説明文。
# ゲーム内アップデートで固有特性が変わった場合は、ここを直接書き換える。
JOB_DETAILS = {
    "戦士": {"summary": "HP・攻撃力・防御力が高く、敵にダメージを与えつつ生き残る力がある。やいばくだきで敵の攻撃力を下げたり、かばうで味方を守ることもできる。すばやさが低いのが弱点。"},
    "僧侶": {"summary": "ホイミ・ベホイミなどでパーティのHP回復源として欠かせない存在。バギ属性の全体攻撃も可能。耐久・攻撃力は低めなので、後衛での運用が向く。"},
    "武闘家": {"summary": "攻撃力とすばやさに優れたアタッカー。必中拳でメタル系にも確実にダメージを与えられる。HP・守備力は低く、前衛配置には不向き。"},
    "魔法使い": {"summary": "高い呪文攻撃力に加えて、バイシオン・ルカニによる支援もできる。紫のこころはHP・みのまもりが低めなので、後衛配置が基本。"},
    "盗賊": {"summary": "毒・麻痺などの状態異常付与率が高く、デュアルカッターで全体攻撃もできる器用な職業。すばやさ強化とも相性が良い。特級職ニンジャへの転職過程で育成されることが多い。"},
    "遊び人": {"summary": "固有特性「あそぶ」により命令を無視してランダムな行動を取ることがあり、扱いづらい。Lv55から直接賢者に転職できる点だけが利点。"},
    "踊り子": {"summary": "いやしのおどりで全体回復ができる貴重な基本職。らせん打ちでの混乱付与、はやぶさ斬りでの単体火力も持つが、こころの色構成（虹/青/緑）はやや不遇。"},
    "バトルマスター": {"traits": [{"name": "怒り", "detail": "ターン開始時たまに斬撃・体技・ブレスダメージアップ"}]},
    "賢者": {"traits": [{"name": "やまびこ", "detail": "呪文をとなえた時たまに2回連続で呪文が発動する。2回目の呪文は威力が減少する。"}]},
    "レンジャー": {"traits": [{"name": "影縛り", "detail": "攻撃時たまに休みを付与する。成功するたびにかかりづらくなる。"}]},
    "魔法戦士": {"traits": [{"name": "フォースブレイク", "detail": "スキル攻撃時、たまにスキルと同じ属性耐性をさげる。すでに耐性が下がっている属性では成功しづらくなる。効果が切れると成功率ももどる。"}]},
    "パラディン": {"traits": [{"name": "パラディンガード", "detail": "まれに仲間ひとりのダメージをすべて引き受け、さらに瀕死ダメージ時HP1で生き残る。かばう使用時は発動できない。"}]},
    "スーパースター": {"traits": [{"name": "ショータイム", "detail": "攻撃か補助スキルを使用した時、まれに仲間ひとりにランダムな良い効果を1〜2段階付与する。ごくまれに仲間全員に付与する場合もある。"}]},
    "海賊": {"traits": [{"name": "威圧", "detail": "斬撃・体技または呪文ダメージを受けたとき、たまに敵を威圧し、相手の攻撃や呪文を弱める（ダーマの試練クリアで「威圧・強」に強化、敵の攻撃をミスさせる確率も追加）。"}]},
    "まものマスター": {"traits": [
        {"name": "スカウトサーチ", "detail": "パーティに参加している間、自身の周辺をサーチしてスカウトできるモンスターの居場所を突き止め、フィールドに出現させる（1日4回まで。ダーマの試練クリアでパーティ外でも使える「いつでもスカウトサーチ」に強化）。"},
        {"name": "ふか名人", "detail": "パーティに参加している間、仲間モンスターのタマゴの孵化が早くなる。"},
    ]},
    "ゴッドハンド": {
        "traits": [
            {"name": "ゴッドレイジ", "detail": "ターン開始時、斬撃・体技・ブレスダメージ+40%。このときレベルに応じてダメージがさらに上昇する(発動確率17%)"},
            {"name": "ゴッドガード", "detail": "仲間ひとりのダメージを10%軽減して全て引き受け、レベルに応じた反撃ダメージを相手にも与える(発動確率25%)。引き受ける時には一部を除く悪い効果を無効化し、致死ダメージ時HP1で生き残り、さらに受けるスキルのHP回復効果が上がる"},
            {"name": "ゴッドチェイン", "detail": "ゴッドレイジとゴッドガードどちらも発動すると会心率とガード率が上昇し、敵に与えた斬撃・体技ダメージに応じて自分のHPを回復する"},
        ],
        "walker_skills": [{"name": "ゴッドパンチ", "detail": "フィールドの戦闘開始直後に神の如き力を宿した拳で、敵全体にレベルに応じたダメージを与える(効果10分)"}],
    },
    "大魔道士": {
        "traits": [
            {"name": "魔人のやまびこ", "detail": "呪文を唱えたとき、2回目の呪文が威力50%で発動する(発動確率15%)"},
            {"name": "フォースブレイク", "detail": "スキル攻撃時、たまにスキルと同じ属性耐性を下げる。すでに耐性が下がっている属性では成功しづらくなる。効果が切れると成功率ももどる"},
            {"name": "連続呪文", "detail": "ターン開始時にごくまれに選択した呪文を2回唱えることができる(2回目の呪文もMPを消費。やまびこも対象となる)また斬撃・体技ダメージを+100%する"},
        ],
        "walker_skills": [{"name": "魔力のたてごと", "detail": "ふしぎな音色でまものを引き寄せる。見かけにくいモンスターはとくにこの音色に引き寄せられる(効果5分)"}],
    },
    "大神官": {
        "traits": [
            {"name": "セイントエコー", "detail": "呪文または回復とくぎ使用時、2回目の呪文または回復とくぎが威力50%で発動する(発動確率15%)"},
            {"name": "鼓舞激励", "detail": "一部を除くスキル使用時、ランダムな良い効果を付与する(発動確率15%)"},
            {"name": "おすそわけ", "detail": "ターン開始時にごくまれに味方1人にかける回復・補助スキルが味方全員にかかるようになる(一部スキルを除く)"},
        ],
        "walker_skills": [{"name": "癒やしの陽光", "detail": "フィールド上で一定時間ごとにHPとMPが最大値の20%回復する(効果20分)"}],
    },
    "ニンジャ": {
        "traits": [
            {"name": "影縫い", "detail": "斬撃・体技・ブレスダメージを与えたとき1回行動の休みを付与し休み中は悪い状態変化をかなり受けやすくなる(発動率15%)成功するたびにかかりづらくなる"},
            {"name": "威圧・強", "detail": "斬撃・体技または呪文ダメージを受けたときたまに敵を威圧・強にする。敵を戦意喪失させたり大海の浪漫を使用するたびに威圧・強の発動率がさがる"},
            {"name": "分身の術", "detail": "行動終了時ごくまれにもう一度行動することができる"},
        ],
        "walker_skills": [{"name": "五感澄明", "detail": "忍びに伝わる秘術でフィールド上のタップできる範囲とこころチャンスの表示範囲を拡大する(効果20分)"}],
    },
    "魔剣士": {
        "traits": [
            {"name": "剣魔合一", "detail": "ターン開始時まれに攻撃時に、こうげき力にこうげき魔力を加える効果を付与する(呪文での攻撃時はこうげき魔力にこうげき力を加える)"},
            {"name": "フォースチャージ", "detail": "属性スキル攻撃時、使用スキルと同じ属性の属性ダメージを1〜2段階上げる(発動率：1段階32%、2段階14%)。1つの属性のダメージは最大6段階まで上昇するが、段階に応じて発動しづらくなる"},
            {"name": "因果", "detail": "ダメージをうけたとき、自分の与えるスキルダメージを1〜2段階上げる(発動率：1段階21%、2段階9%)。因果は最大6段階まで上昇するが、段階に応じて発動しづらくなる"},
        ],
        "walker_skills": [{"name": "勇士召喚", "detail": "ルイーダの酒場にメガモンスターやほこらでのバトルにも参戦する特別な助っ人を呼び出す(呼出可能時間10分)"}],
    },
    "守り人": {
        "traits": [
            {"name": "グレイトウォール", "detail": "味方全体がダメージを受けるとき、自身を除く味方のダメージを10%軽減して、さらに受けるダメージの一部を引き受ける（発動率30%）"},
            {"name": "挑発", "detail": "攻撃スキルで斬撃・体技ダメージを与えた相手をまれに挑発する。挑発された敵は守り人を狙うようになり、狙われたときに受ける単体攻撃のダメージを軽減する"},
            {"name": "いのちのオーラ", "detail": "ダメージをうけた時、まれに斬撃・体技・呪文・ブレスダメージへの耐性を1段階上げる。最大3段階まで上昇するが段階に応じて発動しづらくなる"},
        ],
        "walker_skills": [{"name": "守護者のつばさ", "detail": "フィールド上で見えているメガモンスターやほこらに挑戦できるようになる"}],
    },
    "ドラゴン": {
        "traits": [
            {"name": "竜の血", "detail": "攻撃時またはダメージを受けた時に竜の血が段階的に上昇する(確率で発動、最大で5段階)。竜の血の段階に応じて攻撃力と守備力ときようさが上昇するが4段階以上は自我を保てず制御不能になることがある"},
            {"name": "飢餓", "detail": "行動開始時に一定確率で飢餓状態になる。飢餓の発動中は斬撃・体技・ブレスのダメージが竜の血の段階に応じて上昇し、飢餓中に攻撃行動をおこなうと竜の血の段階が上がる"},
            {"name": "自制心", "detail": "行動開始時に一定確率で自制心を保った状態になる。自制心の発動中は敵から受けるダメージが竜の血の段階に応じて減少し、自制心中に攻撃以外の行動をおこなうと竜の血の段階に応じた量のMPを回復し竜の血の段階が下がる"},
        ],
        "walker_skills": [{"name": "ドラゴンの導き", "detail": "フィールドの戦闘で入手できる導きのかけらとルーラポイントが増加する(効果15分)"}],
    },
    "天地雷鳴士": {
        "traits": [
            {"name": "カカロンの加護［反復］", "detail": "行動開始時まれにカカロンの加護［反復］が与えられる。加護の発動中は敵1体を対象とした攻撃時、ランダムな対象に1~4回追加でダメージを与える(ダメージは減衰し追加効果は与えない)"},
            {"name": "バルバルーの加護［収束］", "detail": "行動開始時まれにバルバルーの加護［収束］が与えられる。加護の発動中は敵全体を対象とした攻撃時に敵の数が少ないほど威力が上昇する"},
            {"name": "ドメディの刻印［奪取］", "detail": "攻撃スキル使用時ごくまれに敵1体と味方の天地雷鳴士にドメディの刻印［奪取］が与えられる。刻印中は刻印がついている敵へ付与される一部の良い効果を奪いとり、刻印がついている味方に付与する"},
        ],
        "walker_skills": [
            {"name": "晴天の儀", "detail": "天地の理を操りフィールドの天候を晴れに変え一部を除く戦闘においてスキルで受けるHP回復効果を1.5倍にする(効果10分)"},
            {"name": "雨天の儀", "detail": "天地の理を操りフィールドの天候を雨に変え一部を除く戦闘においてMP消費量を1/2にする(効果10分)"},
        ],
    },
    "魔人": {
        "traits": [
            {"name": "二刀流", "detail": "一部の武器種において2つの武器を左右の手に装備できる。二刀流中は左手に持った武器の攻撃スキルも使用できるようになり、斬撃・体技の攻撃によるダメージが1度の攻撃で2回発生する"},
            {"name": "痛恨の一撃", "detail": "スキルによる「会心の一撃」「超会心の一撃」発生時のダメージが上昇する"},
            {"name": "根絶やしマインド", "detail": "ターン開始時自身の特殊効果の「系統へのダメージ+」の効果値が上昇する効果を付与する(発動確率20%)"},
        ],
        "walker_skills": [{"name": "魔人の威光", "detail": "モンスターのこころドロップ率をアップする(効果10分)"}],
    },
    "時渡りの剣士": {
        "traits": [
            {"name": "時間レベル", "detail": "MPを消費する行動によって時間レベルが上昇するが、敵からHPダメージを受けるとレベルが下がる(確率で発動、Lv-5からLv5までの10段階)。時間レベルに応じて戦闘中のレベルが変動し、時間レベルが3以上になると確率で自身の行動できる回数が増えるようになるが-3以下になると石化することがある"},
            {"name": "タイムループ", "detail": "行動開始時、時間の歪みが生じてそのターンにスキルで与えるダメージや効果の付与が再現される。時間レベルに応じてダメージや効果付与の再現度が変化(発動確率10%)"},
            {"name": "時間泥棒", "detail": "攻撃スキル使用時対象に付与されている良い効果ターンを奪い、自身に付与されている良い効果ターンを最大+1する。時間レベルに応じて奪う効果数が1〜3個に変化（発動確率10%）"},
        ],
        "walker_skills": [{"name": "加速戦技", "detail": "一部のフィールド戦闘のバトルスピードを1.3倍速にする（効果10分）"}],
    },
    "魔弾の剣士": {
        "traits": [
            {"name": "魔弾生成", "detail": "戦闘開始時および戦闘中の自分以外の味方の固有特性が発動した時に魔弾を生成する"},
            {"name": "ファントムバレット", "detail": "ターン開始時、スキル攻撃時に発生する魔弾効果が上乗せされる(発動確率15%)"},
            {"name": "弾丸パック", "detail": "スキル攻撃後、消費した魔弾の一部が補充される(発動確率15%)"},
        ],
        "walker_skills": [{"name": "威嚇射撃", "detail": "一部のフィールド戦闘で敵のダメージ耐性を20%下げてダメージを与えられるようになる(効果10分)"}],
    },
    "釣り人": {"summary": "バトル向けではなく、新機能「釣り」専用のEX職。自分（主人公）のキャラクターのみ育成でき、パーティメンバーには適用されない。レベルアップで得たスキルポイントで釣り効率アップ系のスキルパネルを解放していく（戦闘用スキルはなし）。Lv50到達後は昇級して全パネルの解放が可能になる。"},
}

# スーパーハイテンション（テンション段階4）時に固有特性が強化される職業。
# GameWith「テンションを上げる・下げる方法と効果」（show/499705）より書き起こし。
TENSION_BONUS = {
    "ゴッドハンド": "ゴッドレイジ・ゴッドガードの発動率2倍",
    "バトルマスター": "怒り・激怒の発動率2倍",
    "大魔道士": "フォースブレイク・魔人のやまびこの発動率+100%",
    "賢者": "やまびこ・やまびこのさとりの発動率+100%",
    "魔法戦士": "フォースブレイクの発動率+100%",
    "大神官": "鼓舞激励の発動率3倍・全体効果確率2倍",
    "スーパースター": "ショータイムの発動率2倍・全体効果確率2倍",
    "ニンジャ": "影縫い付与時に敵の耐性を無視",
    "レンジャー": "影縛り付与時に敵の耐性を無視",
    "守り人": "グレイトウォール発動時の軽減率2倍",
    "ドラゴン": "竜の血がLv5になり制御不能にならない",
    "時渡りの剣士": "タイムループ・時間泥棒の発動率2倍",
    "天地雷鳴士": "カカロンの加護【反撃】を付与（効果3ターン）",
    "魔人": "会心率を1段階上げる効果を付与（効果4ターン）",
    "魔剣士": "因果とフォースチャージの段階を同期・引き上げ",
    "パラディン": "パラディンガードの発動率2倍",
}

# ゾーン中の職業別ボーナス（自身への効果／味方への効果）。
# GameWith「ゾーンの効果と発動条件・使えるスキル」（show/561785）より書き起こし。
ZONE_BONUS = {
    "self_150": {"self": "スキルダメージ+150%", "ally": "スキルダメージ+45%",
                 "jobs": ["ゴッドハンド", "時渡りの剣士", "ドラゴン", "バトルマスター", "スーパースター"]},
    "crit_dmg_230": {"self": "スキルの会心・暴走ダメージ+230%", "ally": "スキルの会心・暴走ダメージ+69%",
                      "jobs": ["大魔道士", "魔人", "海賊", "まものマスター"]},
    "crit_rate_40": {"self": "会心率・暴走率+40%", "ally": "会心率・暴走率+12%",
                       "jobs": ["大神官", "ニンジャ", "守り人", "賢者", "レンジャー", "パラディン"]},
    "element_150": {"self": "全属性ダメージ+150%", "ally": "全属性ダメージ+45%",
                     "jobs": ["魔剣士", "天地雷鳴士", "魔法戦士"]},
}
ZONE_BONUS_BY_JOB = {job: {"self": group["self"], "ally": group["ally"]} for group in ZONE_BONUS.values() for job in group["jobs"]}


def download_overview_tables():
    print("職業一覧ページを取得中...")
    html = download(OVERVIEW_PAGE)
    tables = re.findall(r"<table><tr><th>職業</th>.*?</table>", html, re.S)
    if len(tables) != 3:
        raise RuntimeError(f"職業テーブルの数が想定と違います（{len(tables)}個）。ページ構成が変わった可能性があります。")

    category_by_table = ["特級職", "上級職", "基本職"]
    jobs = []
    for table_html, category in zip(tables, category_by_table):
        parser = TableParser()
        parser.feed(table_html)
        for row, image, link in zip(parser.rows[1:], parser.row_images[1:], parser.row_links[1:]):
            name = row[0]
            weapons_text = row[2] if category == "特級職" else row[1]
            heart_text = row[3] if category == "特級職" else row[2]
            jobs.append({
                "name": name,
                "category": category,
                "weapons": WEAPON_PATTERN.findall(weapons_text),
                "heart_slots": HEART_SLOT_PATTERN.findall(heart_text),
                "icon_url": image,
                "detail_url": link,
            })
    # EX職（釣り人）はこの3つの表に含まれないため、手動で追加
    jobs.append({
        "name": "釣り人",
        "category": "EX職",
        "weapons": [],
        "heart_slots": [],
        "icon_url": TSURIBITO_ICON,
        "detail_url": TSURIBITO_LINK,
    })
    return jobs


def download_heart_color_icons():
    HEART_COLOR_ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon_map = {}
    for label, filename in HEART_COLOR_ICONS.items():
        image_path = HEART_COLOR_ICON_DIR / f"{filename}.png"
        try:
            if not image_path.exists():
                download_binary(HEART_COLOR_ICON_BASE + filename + ".png", image_path)
                time.sleep(0.2)
            icon_map[label] = f"images/heart_colors/{filename}.png"
        except Exception as error:
            print(f"こころ枠アイコンを取得できませんでした: {label} ({error})")
    return icon_map


def main():
    jobs = download_overview_tables()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    heart_color_icons = download_heart_color_icons()

    for job in jobs:
        slug = re.sub(r"[^a-z0-9]+", "", job["icon_url"].rsplit("/", 1)[-1].replace("_i.png", "").lower()) or job["name"]
        image_path = IMAGE_DIR / f"{slug}.png"
        try:
            if not image_path.exists():
                download_binary(job["icon_url"], image_path)
                time.sleep(0.2)
            job["image_path"] = f"images/jobs/{slug}.png"
        except Exception as error:
            print(f"画像を取得できませんでした: {job['name']} ({error})")
        del job["icon_url"]

        details = JOB_DETAILS.get(job["name"], {})
        if "traits" in details:
            job["traits"] = details["traits"]
        if "walker_skills" in details:
            job["walker_skills"] = details["walker_skills"]
        if "summary" in details:
            job["summary"] = details["summary"]
        if job["name"] in TENSION_BONUS:
            job["tension_bonus"] = TENSION_BONUS[job["name"]]
        if job["name"] in ZONE_BONUS_BY_JOB:
            job["zone_bonus"] = ZONE_BONUS_BY_JOB[job["name"]]

    JOBS_FILE.write_text(json.dumps({"jobs": jobs, "heart_color_icons": heart_color_icons}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(jobs)}件の職業データを jobs.json に書き出しました。")


if __name__ == "__main__":
    main()
