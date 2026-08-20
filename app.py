"""AI Writing Studio — Streamlit + Gemini API による個人用ライティングツール。

起動（PowerShell。streamlit は .venv の中にしか無いのでフルパスで呼ぶ）:
    .\\.venv\\Scripts\\streamlit.exe run app.py

run.bat をダブルクリックしても同じ。あちらは先に .venv を有効化するので、
その場合だけ `streamlit run app.py` と素で打てる。
"""

import streamlit as st

import config
from core import gemini
from features import (
    blog,
    chat,
    history_view,
    idea,
    mail,
    proofread,
    rewrite,
    sns,
    summarize,
    translate,
)

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)


def home() -> None:
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.caption("書く・直す・まとめる。日々の文章仕事をまとめて片付けるための個人用ツールです。")
    st.divider()

    tools = [
        ("📝", "ブログ記事執筆", "構成案から本文まで、2ステップで記事を書き上げる"),
        ("📧", "メール返信作成", "受信メールを貼るだけで返信の下書きをつくる"),
        ("📄", "文章要約", "長文・議事録・PDFを目的に合った形にまとめる"),
        ("🔍", "校正・推敲", "誤字や敬語を直し、修正箇所を一覧で示す"),
        ("🔄", "リライト", "同じ内容を別の文体・長さ・読者向けに書き換える"),
        ("📱", "SNS投稿文", "媒体の作法に合わせた投稿文を複数案つくる"),
        ("💡", "タイトル・コピー", "切り口を変えたアイデアをまとめて出す"),
        ("🌐", "翻訳", "文体と用語集を指定して訳す"),
        ("💬", "自由チャット", "役割を選んで対話しながら文章を詰める"),
    ]
    for icon, name, description in tools:
        st.markdown(f"**{icon} {name}** — {description}")

    st.divider()
    st.info("左のサイドバーからツールを選んでください。生成結果は「🗂️ 生成履歴」に自動保存されます。")


def sidebar() -> None:
    """全ページ共通の設定パネル。"""
    with st.sidebar:
        st.markdown(f"### {config.APP_ICON} {config.APP_TITLE}")

        with st.expander("⚙️ 生成設定", expanded=False):
            label = st.selectbox("モデル", list(config.MODELS.keys()), key="model_label")
            st.session_state["model"] = config.MODELS[label]

            st.slider(
                "創造性（Temperature）",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                step=0.1,
                key="temperature",
                help="低いほど堅実で安定、高いほど自由で意外性のある文章になります。",
            )
            level_label = st.selectbox(
                "思考レベル",
                list(config.THINKING_LEVELS.keys()),
                index=1,
                help="高いほどじっくり考えて品質が上がり、低いほど速く安くなります。",
            )
            st.session_state["thinking_level"] = config.THINKING_LEVELS[level_label]

        with st.expander("🔑 APIキー", expanded=not gemini.resolve_api_key()):
            st.text_input(
                "Gemini APIキー",
                type="password",
                key="api_key_input",
                help=".env に GEMINI_API_KEY を書いておけば、毎回の入力は不要です。",
            )
            st.caption("[Google AI Studio で取得](https://aistudio.google.com/apikey)")

        if gemini.resolve_api_key():
            st.success("APIキー: 設定済み", icon="✅")
        else:
            st.error("APIキーが未設定です", icon="⚠️")


def main() -> None:
    sidebar()

    navigation = st.navigation(
        {
            "ホーム": [
                st.Page(home, title="ホーム", icon="🏠", url_path="home", default=True),
            ],
            "書く": [
                st.Page(blog.render, title="ブログ記事", icon="📝", url_path="blog"),
                st.Page(mail.render, title="メール返信", icon="📧", url_path="mail"),
                st.Page(sns.render, title="SNS投稿文", icon="📱", url_path="sns"),
                st.Page(idea.render, title="タイトル・コピー", icon="💡", url_path="idea"),
            ],
            "直す・まとめる": [
                st.Page(summarize.render, title="要約", icon="📄", url_path="summarize"),
                st.Page(proofread.render, title="校正・推敲", icon="🔍", url_path="proofread"),
                st.Page(rewrite.render, title="リライト", icon="🔄", url_path="rewrite"),
                st.Page(translate.render, title="翻訳", icon="🌐", url_path="translate"),
            ],
            "その他": [
                st.Page(chat.render, title="自由チャット", icon="💬", url_path="chat"),
                st.Page(history_view.render, title="生成履歴", icon="🗂️", url_path="history"),
            ],
        }
    )
    navigation.run()


if __name__ == "__main__":
    main()
