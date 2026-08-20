"""SNS投稿文の作成。"""

import streamlit as st

import config
from core import ui

FEATURE = "SNS投稿"

PLATFORMS = {
    "X（旧Twitter）": "140文字以内に収める。改行を使って読みやすく。1投稿で完結させる。",
    "X（連投スレッド）": "3〜5投稿のスレッド。各投稿は140文字以内で、(1/5) のような番号を付ける。1投稿目で必ず惹きつける。",
    "Instagram": "冒頭2行で惹きつける。改行を多めに、絵文字も適度に使う。最後にハッシュタグをまとめる。",
    "Facebook": "300〜500文字。ストーリー性を持たせ、最後に問いかけで締める。",
    "LinkedIn": "ビジネス文脈。実績・学び・示唆を中心に、絵文字は控えめ。400文字前後。",
    "note / ブログ告知": "記事に興味を持たせる紹介文。内容の一部を見せて続きが読みたくなるようにする。",
}


def _prompt(topic: str, platform: str, tone: str, cta: str, hashtags: int, emoji: bool, count: int) -> str:
    return f"""SNSの投稿文を作ってください。

# 投稿したい内容
{topic}

# プラットフォームの作法
{PLATFORMS[platform]}

# 条件
- トーン: {tone}
- 絵文字: {'適度に使う' if emoji else '使わない'}
- ハッシュタグ: {f'{hashtags}個ほど付ける' if hashtags else '付けない'}
- 誘導したい行動（CTA）: {cta or '特になし'}

# 出力ルール
- 切り口の違う案を{count}つ出す。それぞれ「### 案1：（切り口の名前）」の形式で見出しを付ける。
- 投稿文はそのままコピーして貼れる形で書く。解説は書かない。
- 誇大表現や事実でない断定はしない。"""


def render() -> None:
    ui.page_header("📱", "SNS投稿文", "伝えたいことから、媒体の作法に合わせた投稿文を複数案つくります。")

    topic = st.text_area(
        "投稿したい内容 **必須**",
        height=140,
        placeholder="例）新しくブログ記事を公開した。在宅ワークの集中力を保つ時間管理術について書いた。",
    )

    col1, col2 = st.columns(2)
    platform = col1.selectbox("プラットフォーム", list(PLATFORMS.keys()))
    tone = col2.selectbox("トーン", config.TONES, index=1)

    col3, col4, col5 = st.columns(3)
    count = col3.number_input("案の数", min_value=1, max_value=5, value=3)
    hashtags = col4.number_input("ハッシュタグの数", min_value=0, max_value=10, value=3)
    emoji = col5.checkbox("絵文字を使う", value=True)

    cta = st.text_input(
        "誘導したい行動（任意）", placeholder="例）プロフィールのリンクから記事を読んでもらう"
    )

    if st.button("投稿文を作る", type="primary", use_container_width=True):
        if ui.require_input(topic, "投稿したい内容を入力してください。"):
            ui.generate(
                "sns_result",
                feature=FEATURE,
                title=f"{platform}：{topic[:30]}…",
                prompt=_prompt(topic, platform, tone, cta, int(hashtags), emoji, int(count)),
            )

    ui.show_result("sns_result", filename_stem="sns_post")
