"""翻訳。用語集と文体指定に対応する。"""

import streamlit as st

import config
from core import ui
from core.prompt import data_block

FEATURE = "翻訳"

STYLES = {
    "自然な訳（意訳寄り）": "直訳調を避け、その言語のネイティブが自然に読める文章にする。",
    "忠実な訳（直訳寄り）": "原文の構造と情報をできるだけ保つ。省略・補足をしない。",
    "ビジネス文書": "ビジネス文書として適切な語彙と丁寧さで訳す。",
    "カジュアル・口語": "友人に話すような、くだけた自然な言い回しにする。",
    "技術文書": "技術用語を正確に扱い、簡潔で曖昧さのない文にする。",
}


def _prompt(text: str, src: str, dst: str, style: str, glossary: str, explain: bool) -> str:
    extra = (
        "\n\n翻訳文の後に「## 訳注」として、意訳した箇所やニュアンスの補足を3点以内で書く。"
        if explain
        else "\n\n翻訳文のみを出力し、解説・前置きは書かない。"
    )
    return f"""次の文章を{src}から{dst}に翻訳してください。

# 翻訳スタイル
{STYLES[style]}

# 用語集（この対訳を必ず守る）
{glossary or '指定なし'}

# ルール
- 原文の意味・トーン・敬語のレベルを保つ。
- 固有名詞、製品名、数値は勝手に変えない。
- 原文にない情報を足さない。{extra}

# 原文
{data_block(text, "原文")}"""


def render() -> None:
    ui.page_header("🌐", "翻訳", "文体と用語集を指定して、用途に合った訳文をつくります。")

    text = ui.source_text_input(
        "翻訳したい文章 **必須**",
        key="tr_src",
        height=260,
        placeholder="ここに原文を貼り付けてください。",
    )

    col1, col2, col3 = st.columns(3)
    src = col1.selectbox("原文の言語", ["自動判別"] + config.LANGUAGES)
    dst = col2.selectbox("翻訳先の言語", config.LANGUAGES, index=1)
    style = col3.selectbox("翻訳スタイル", list(STYLES.keys()))

    glossary = st.text_area(
        "用語集（任意・1行に1組）",
        height=90,
        placeholder="例）\n弊社 = our company\n案件 = project",
    )
    explain = st.checkbox("訳注（ニュアンスの補足）を付ける", value=False)

    if st.button("翻訳する", type="primary", use_container_width=True):
        if ui.require_input(text, "翻訳したい文章を入力してください。"):
            ui.generate(
                "tr_result",
                feature=FEATURE,
                title=f"{src}→{dst}：{text[:30]}…",
                prompt=_prompt(text, src, dst, style, glossary, explain),
            )

    ui.show_result("tr_result", filename_stem="translation")
