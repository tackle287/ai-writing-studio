"""ブログ記事執筆：構成案 → 本文 の2ステップで書く。"""

import streamlit as st

import config
from core import ui

FEATURE = "ブログ記事"

ARTICLE_TYPES = [
    "ハウツー・解説",
    "レビュー・比較",
    "体験談・エッセイ",
    "ニュース解説",
    "まとめ・リスト記事",
    "入門ガイド",
]


def _spec_block(p: dict) -> str:
    return f"""# 記事の条件
- テーマ: {p['theme']}
- 記事タイプ: {p['article_type']}
- 想定読者: {p['audience']}
- トーン: {p['tone']}
- 目標文字数: 約{p['length']}文字
- 狙うキーワード: {p['keywords'] or '指定なし'}
- 補足情報・盛り込みたい要素: {p['notes'] or '特になし'}"""


def _outline_prompt(p: dict) -> str:
    return f"""次の条件でブログ記事の構成案を作ってください。

{_spec_block(p)}

# 出力形式
1. 記事タイトル案を3つ（それぞれ30文字前後、クリックしたくなるもの）
2. リード文の要旨（100文字程度で、何を書くかの説明）
3. 見出し構成（## と ### のMarkdown見出し。各見出しの下に「何を書くか」を1〜2行のメモで添える）
4. まとめで伝えること

本文そのものはまだ書かないでください。"""


def _draft_prompt(p: dict, outline: str) -> str:
    return f"""次の構成案に沿って、ブログ記事の本文を書いてください。

{_spec_block(p)}

# 構成案
{outline}

# 執筆ルール
- Markdown形式。記事タイトルは # 、章は ## 、小見出しは ### を使う。
- 冒頭のリード文で、読者の悩みと記事を読むメリットを示す。
- 抽象論で終わらせず、具体例・数字・手順を入れる。
- 1段落は3行以内。読みやすさを優先し、適宜箇条書きや表を使う。
- 「〜と言えるでしょう」「いかがでしたか」のような中身のない常套句は使わない。
- 目標文字数に近づける。"""


def render() -> None:
    ui.page_header("📝", "ブログ記事執筆", "構成案をつくって整えてから、本文を一気に書き上げます。")

    # 構成案の生成結果を、編集用テキストエリアに反映させる（ウィジェット生成前に行う）
    generated = st.session_state.pop("blog_outline_gen", None)
    if generated is not None:
        st.session_state["blog_outline"] = generated

    theme = st.text_input(
        "テーマ・書きたいこと **必須**",
        placeholder="例）在宅ワークで集中力を保つための時間管理術",
    )

    col1, col2 = st.columns(2)
    article_type = col1.selectbox("記事タイプ", ARTICLE_TYPES)
    audience = col2.selectbox("想定読者", config.AUDIENCES)

    col3, col4 = st.columns(2)
    tone = col3.selectbox("トーン", config.TONES)
    length = col4.select_slider(
        "目標文字数", options=[800, 1500, 2500, 4000, 6000], value=2500
    )

    keywords = st.text_input(
        "SEOキーワード（任意・カンマ区切り）", placeholder="例）在宅ワーク, 集中力, ポモドーロ"
    )
    notes = st.text_area(
        "補足情報・盛り込みたい要素（任意）",
        height=100,
        placeholder="例）自分の失敗談を入れたい / 最後に無料ツールを3つ紹介する",
    )

    params = {
        "theme": theme,
        "article_type": article_type,
        "audience": audience,
        "tone": tone,
        "length": length,
        "keywords": keywords,
        "notes": notes,
    }

    st.divider()
    st.markdown("### ① 構成案をつくる")
    run_outline = st.button("構成案を生成", type="primary", use_container_width=True)

    outline = st.text_area(
        "構成案（自由に書き換えてから本文生成に進めます）",
        height=320,
        key="blog_outline",
        placeholder="ここに構成案が入ります。自分で直接書いてもOKです。",
    )

    st.markdown("### ② 本文を書く")
    run_draft = st.button(
        "この構成案で本文を生成", type="primary", use_container_width=True, disabled=not outline
    )

    ui.show_result("blog_draft", filename_stem="blog")

    if run_outline and ui.require_input(theme, "テーマを入力してください。"):
        ui.generate(
            "blog_outline_gen",
            feature=f"{FEATURE}（構成案）",
            title=theme,
            prompt=_outline_prompt(params),
        )

    if run_draft and ui.require_input(theme, "テーマを入力してください。"):
        ui.generate(
            "blog_draft",
            feature=FEATURE,
            title=theme,
            prompt=_draft_prompt(params, outline),
        )
