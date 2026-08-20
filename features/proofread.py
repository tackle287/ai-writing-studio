"""校正・推敲：修正版と指摘一覧を出す。"""

import streamlit as st

from core import ui
from core.prompt import data_block

FEATURE = "校正・推敲"

CHECKS = {
    "誤字脱字・変換ミス": "誤字、脱字、変換ミス、タイプミス",
    "文法・係り受け": "文法の誤り、主語と述語のねじれ、係り受けの曖昧さ",
    "表記ゆれ": "同じ語の表記ゆれ、送り仮名の不統一、全角半角の混在",
    "敬語・ビジネス表現": "敬語の誤用、二重敬語、失礼に受け取られる表現",
    "冗長表現": "回りくどい言い回し、重複表現、不要な修飾語",
    "読みやすさ": "一文の長さ、漢字とひらがなのバランス、段落の区切り",
    "論理の飛躍": "根拠のない断定、話の飛躍、矛盾",
}


def _prompt(text: str, checks: list[str], style: str, strength: str) -> str:
    check_lines = "\n".join(f"- {CHECKS[c]}" for c in checks)
    return f"""次の文章を校正・推敲してください。

# チェック観点
{check_lines}

# 文体の指定
{style or '原文の文体を維持する'}

# 修正の強さ
{strength}

# 出力形式（この2部構成を厳守）
## 修正後の文章
（修正を反映した全文。ここには説明を書かない）

## 指摘一覧
| # | 元の表現 | 修正後 | 種別 | 理由 |
|---|---------|-------|------|------|
（修正した箇所を1行ずつ。修正が不要だった場合は「指摘なし」と書く）

# 注意
- 内容そのものは変えない。事実や主張の追加・削除をしない。
- 原文にない情報を補わない。

# 原文
{data_block(text, "原文")}"""


def render() -> None:
    ui.page_header("🔍", "校正・推敲", "誤字脱字から敬語・冗長表現まで直し、どこを直したかを一覧で示します。")

    text = ui.source_text_input(
        "校正したい文章 **必須**",
        key="proof_src",
        height=300,
        placeholder="ここに文章を貼り付けてください。",
    )

    checks = st.multiselect(
        "チェックする観点",
        list(CHECKS.keys()),
        default=["誤字脱字・変換ミス", "文法・係り受け", "表記ゆれ", "冗長表現"],
    )

    col1, col2 = st.columns(2)
    style = col1.text_input(
        "文体の指定（任意）", placeholder="例）です・ます調 / 常体（だ・である調）"
    )
    strength = col2.select_slider(
        "修正の強さ",
        options=[
            "最小限（明確な誤りだけ直す）",
            "標準（読みやすさも整える）",
            "積極的（構成や言い回しも踏み込んで改善する）",
        ],
        value="標準（読みやすさも整える）",
    )

    if st.button("校正する", type="primary", use_container_width=True):
        if ui.require_input(text, "校正したい文章を入力してください。") and checks:
            ui.generate(
                "proof_result",
                feature=FEATURE,
                title=(text[:40] + "…") if len(text) > 40 else text,
                prompt=_prompt(text, checks, style, strength),
            )
        elif not checks:
            st.warning("チェックする観点を1つ以上選んでください。")

    ui.show_result("proof_result", filename_stem="proofread")
