"""各ページで使い回す共通UIパーツ。"""

from __future__ import annotations

import io
from datetime import datetime

import streamlit as st

import config
from core import gemini, history


# ---------------------------------------------------------------- 設定 / ヘッダ

def settings() -> dict:
    """サイドバーで選んだ生成設定を取り出す。"""
    return {
        "model": st.session_state.get("model", config.DEFAULT_MODEL),
        "temperature": st.session_state.get("temperature", 0.7),
        "thinking_level": st.session_state.get(
            "thinking_level", config.DEFAULT_THINKING_LEVEL
        ),
    }


def page_header(icon: str, title: str, description: str) -> None:
    st.title(f"{icon} {title}")
    st.caption(description)
    st.divider()


# ---------------------------------------------------------------- 入力ヘルパー

def read_uploaded_file(uploaded) -> str:
    """アップロードされた txt / md / pdf からテキストを取り出す。"""
    if uploaded is None:
        return ""

    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            st.error("PDFを読むには pypdf が必要です: pip install pypdf")
            return ""
        reader = PdfReader(io.BytesIO(uploaded.getvalue()))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)

    return uploaded.getvalue().decode("utf-8", errors="replace")


def source_text_input(label: str, key: str, height: int = 260, placeholder: str = "") -> str:
    """テキスト直接入力とファイル読み込みを兼ねた入力欄。"""
    text_key = f"{key}_text"
    uploaded = st.file_uploader(
        "ファイルから読み込む（任意・txt / md / pdf）",
        type=["txt", "md", "pdf"],
        key=f"{key}_file",
    )
    if uploaded is not None:
        # 同じファイルで再描画されるたびに上書きしないよう、署名で判定する
        signature = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get(f"{key}_loaded") != signature:
            st.session_state[text_key] = read_uploaded_file(uploaded)
            st.session_state[f"{key}_loaded"] = signature

    text = st.text_area(label, height=height, key=text_key, placeholder=placeholder)
    if text:
        st.caption(f"入力: {len(text):,} 文字")
    return text


# ---------------------------------------------------------------- 生成 / 結果表示

def generate(
    state_key: str,
    *,
    feature: str,
    title: str,
    prompt,
    system_instruction: str | None = None,
) -> None:
    """ストリーミング生成 → session_state と履歴に保存 → 再描画。"""
    conf = settings()
    system = system_instruction or config.BASE_SYSTEM

    st.markdown("#### 生成中…")
    box = st.container(border=True)
    try:
        with box:
            text = st.write_stream(
                gemini.stream_generate(
                    prompt,
                    system_instruction=system,
                    model=conf["model"],
                    temperature=conf["temperature"],
                    thinking_level=conf["thinking_level"],
                )
            )
    except Exception as e:  # APIエラー全般（キー不正・レート制限・混雑など）
        st.error(gemini.friendly_error(e))
        return

    if not text:
        st.warning("空の応答が返ってきました。入力内容を変えて試してください。")
        return

    st.session_state[state_key] = text
    history.add(feature=feature, title=title, output=text, model=conf["model"])
    st.rerun()


def _clear(state_key: str) -> None:
    st.session_state.pop(state_key, None)


def show_result(state_key: str, filename_stem: str = "output") -> None:
    """保存済みの生成結果を、プレビュー / コピー / ダウンロード付きで表示する。"""
    text = st.session_state.get(state_key)
    if not text:
        return

    st.markdown("#### 生成結果")
    preview_tab, raw_tab = st.tabs(["プレビュー", "コピー用テキスト"])
    with preview_tab:
        st.markdown(text)
    with raw_tab:
        # st.code の右上のアイコンでワンクリックコピーできる
        st.code(text, language="markdown", wrap_lines=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "⬇️ .md で保存",
        text,
        file_name=f"{filename_stem}_{stamp}.md",
        mime="text/markdown",
        use_container_width=True,
        key=f"{state_key}_dl_md",
    )
    col2.download_button(
        "⬇️ .txt で保存",
        text,
        file_name=f"{filename_stem}_{stamp}.txt",
        mime="text/plain",
        use_container_width=True,
        key=f"{state_key}_dl_txt",
    )
    col3.button(
        "🗑️ 結果をクリア",
        use_container_width=True,
        key=f"{state_key}_clear",
        on_click=_clear,
        args=(state_key,),
    )
    st.caption(f"出力: {len(text):,} 文字")


def require_input(value: str, message: str) -> bool:
    """必須入力のチェック。空なら警告を出して False を返す。"""
    if not value or not value.strip():
        st.warning(message)
        return False
    return True
