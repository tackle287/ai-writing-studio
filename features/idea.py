"""キャッチコピー・タイトル案・アイデア出し。"""

import streamlit as st

import config
from core import ui

FEATURE = "アイデア出し"

KINDS = {
    "記事・動画のタイトル": "クリックしたくなるタイトル。30文字前後。数字・具体性・意外性のいずれかを含める。",
    "キャッチコピー": "商品やサービスの魅力を一言で伝えるコピー。20文字以内で、リズムを重視する。",
    "メールの件名": "開封したくなる件名。20文字前後で、用件が一目で分かる。",
    "プレゼンのタイトル": "聞き手の関心を引き、内容が想像できるタイトル。",
    "商品・サービス名": "覚えやすく、読み方が明快で、意味が想像できる名前。読み仮名も添える。",
    "記事のネタ出し": "そのテーマで書けるブログ記事のネタ。それぞれ想定読者と切り口を添える。",
    "構成のアイデア": "その内容を伝えるための構成パターン。それぞれ流れを3〜5ステップで示す。",
}


def _prompt(topic: str, kind: str, count: int, direction: str, audience: str, notes: str) -> str:
    return f"""アイデア出しをお願いします。

# 対象
{topic}

# 出してほしいもの
{KINDS[kind]}

# 条件
- 個数: {count}個
- 想定読者・ターゲット: {audience}
- 方向性: {direction or '幅広く、切り口の違うものを混ぜる'}
- 補足: {notes or '特になし'}

# 出力形式
番号付きリストで出す。各案の後ろに「— （狙い・刺さる理由を15文字程度で）」を添える。
似た案を並べず、切り口をはっきり変える。最後に「一番のおすすめ: 」として1つ選び、理由を1行で書く。"""


def render() -> None:
    ui.page_header("💡", "タイトル・コピー・ネタ出し", "切り口を変えた案をまとめて出して、選べる状態にします。")

    topic = st.text_area(
        "対象（何についての案が欲しいか） **必須**",
        height=120,
        placeholder="例）在宅ワークの集中力を保つ時間管理術についてのブログ記事",
    )

    col1, col2, col3 = st.columns(3)
    kind = col1.selectbox("出したいもの", list(KINDS.keys()))
    count = col2.number_input("個数", min_value=3, max_value=30, value=10)
    audience = col3.selectbox("ターゲット", config.AUDIENCES)

    direction = st.text_input(
        "方向性（任意）", placeholder="例）煽らず、誠実な印象で / 数字を入れて"
    )
    notes = st.text_input("補足（任意）", placeholder="例）「時短」という言葉は使わない")

    if st.button("アイデアを出す", type="primary", use_container_width=True):
        if ui.require_input(topic, "対象を入力してください。"):
            ui.generate(
                "idea_result",
                feature=FEATURE,
                title=f"{kind}：{topic[:30]}…",
                prompt=_prompt(topic, kind, int(count), direction, audience, notes),
            )

    ui.show_result("idea_result", filename_stem="ideas")
