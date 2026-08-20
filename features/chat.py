"""自由チャット：役割を切り替えて、対話しながら文章を詰める。"""

import streamlit as st

import config
from core import gemini, ui

FEATURE = "チャット"
STATE = "chat_messages"

ROLES = {
    "汎用ライティング": config.BASE_SYSTEM,
    "厳しい編集者": (
        config.BASE_SYSTEM
        + "あなたはベテランの編集者です。提示された文章に対して、褒めるより先に問題点を指摘します。"
        "曖昧な表現、根拠のない主張、冗長な箇所を具体的に指摘し、必ず代案を示します。"
    ),
    "壁打ち相手": (
        "あなたは思考の整理を助ける対話相手です。すぐに答えを出さず、"
        "相手の考えを引き出す質問を1〜2個ずつ投げ返します。"
        "話が固まってきたら、要点を箇条書きで整理して見せます。"
    ),
    "取材ライター": (
        config.BASE_SYSTEM
        + "あなたは取材ライターです。相手の体験や考えを引き出す質問をし、"
        "十分な材料が集まったら、聞き取った内容だけを使って文章にまとめます。"
    ),
    "説明の先生": (
        "あなたは難しいことをやさしく説明する先生です。専門用語には必ず注釈を付け、"
        "身近な例えを使い、最後に一言でまとめます。"
    ),
}


def _messages() -> list[dict]:
    return st.session_state.setdefault(STATE, [])


def render() -> None:
    ui.page_header("💬", "自由チャット", "役割を選んで、対話しながら文章を詰めていきます。")

    col1, col2 = st.columns([3, 1])
    role = col1.selectbox("AIの役割", list(ROLES.keys()), key="chat_role")
    col2.button(
        "🗑️ 会話をリセット",
        use_container_width=True,
        on_click=lambda: st.session_state.update({STATE: []}),
    )

    with st.expander("システムプロンプトを自分で書く（任意）"):
        custom = st.text_area(
            "指定するとロール選択より優先されます",
            height=120,
            key="chat_custom_system",
            placeholder="例）あなたは私の note の共同執筆者です。常体で、比喩を多めに書いてください。",
        )

    system = custom.strip() if custom and custom.strip() else ROLES[role]
    messages = _messages()

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("メッセージを入力（Shift+Enterで改行）"):
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        conf = ui.settings()
        with st.chat_message("assistant"):
            try:
                reply = st.write_stream(
                    gemini.stream_generate(
                        gemini.to_contents(messages),
                        system_instruction=system,
                        model=conf["model"],
                        temperature=conf["temperature"],
                        thinking_level=conf["thinking_level"],
                    )
                )
            except Exception as e:
                st.error(gemini.friendly_error(e))
                messages.pop()  # 失敗したユーザー発言は履歴に残さない
                return

        messages.append({"role": "assistant", "content": reply})
        st.rerun()

    if messages:
        log = "\n\n".join(
            f"### {'あなた' if m['role'] == 'user' else 'AI'}\n{m['content']}" for m in messages
        )
        st.download_button(
            "⬇️ 会話ログを保存",
            log,
            file_name="chat_log.md",
            mime="text/markdown",
        )
