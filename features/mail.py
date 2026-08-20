"""メール返信文の作成。"""

import streamlit as st

import config
from core import ui
from core.prompt import data_block

FEATURE = "メール返信"

RELATIONS = ["社外・取引先", "社外・初めての相手", "顧客・お客様", "社内・上司", "社内・同僚", "友人・知人"]
LENGTHS = {"簡潔（3〜5行）": "3〜5行の簡潔な本文", "標準": "200文字前後の本文", "丁寧・長め": "背景説明を含む400文字程度の本文"}
STANCES = [
    "承諾する",
    "丁重に断る",
    "日程を調整・提案する",
    "質問・確認する",
    "お礼を伝える",
    "お詫びする",
    "催促する",
    "情報を提供する",
    "その他（要点欄に記載）",
]


def _prompt(received: str, points: str, relation: str, stance: str, tone: str, length: str, sign: str) -> str:
    return f"""次の受信メールに対する返信文を作成してください。

# 受信したメール
{data_block(received, "受信メール")}

# 返信の条件
- 相手との関係: {relation}
- 返信のスタンス: {stance}
- 必ず伝えたい要点: {points or '（受信内容から適切に判断する）'}
- トーン: {tone}
- 分量: {LENGTHS[length]}
- 差出人の署名: {sign or '（署名は書かない）'}

# 出力形式
件名: （Re: を含む適切な件名）

（本文。宛名 → 挨拶 → 用件 → 結びの順。日本のビジネスメールの慣習に沿う）

# 注意
- 受信メールに書かれていない事実（日程・金額・担当者名など）を勝手に作らない。埋めるべき箇所は [ ] で示す。
- 相手の名前や会社名は受信メールから読み取って使う。読み取れない場合は [お名前] とする。"""


def render() -> None:
    ui.page_header("📧", "メール返信作成", "受け取ったメールを貼り付けるだけで、返信文の下書きを作ります。")

    received = ui.source_text_input(
        "受信したメール本文 **必須**",
        key="mail_src",
        height=220,
        placeholder="受け取ったメールをそのまま貼り付けてください。",
    )

    col1, col2 = st.columns(2)
    relation = col1.selectbox("相手との関係", RELATIONS)
    stance = col2.selectbox("返信のスタンス", STANCES)

    points = st.text_area(
        "返信で伝えたい要点（箇条書きでOK）",
        height=100,
        placeholder="例）\n・26日の打ち合わせはOK\n・場所はこちらの会議室を希望\n・資料は前日までに送る",
    )

    col3, col4 = st.columns(2)
    tone = col3.selectbox("トーン", config.TONES)
    length = col4.selectbox("分量", list(LENGTHS.keys()), index=1)

    sign = st.text_input("署名（任意）", placeholder="例）株式会社〇〇 営業部 山田太郎")

    if st.button("返信文を作成", type="primary", use_container_width=True):
        if ui.require_input(received, "受信したメール本文を貼り付けてください。"):
            ui.generate(
                "mail_result",
                feature=FEATURE,
                title=(received[:40] + "…") if len(received) > 40 else received,
                prompt=_prompt(received, points, relation, stance, tone, length, sign),
            )

    ui.show_result("mail_result", filename_stem="mail_reply")
