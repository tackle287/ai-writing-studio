"""生成履歴の閲覧。"""

import json

import streamlit as st

from core import history, ui


def render() -> None:
    ui.page_header("🗂️", "生成履歴", "これまでの生成結果をローカルに保存しています（data/history.jsonl）。")

    records = history.load()
    if not records:
        st.info("まだ履歴がありません。各ツールで文章を生成すると、ここに残ります。")
        return

    features = sorted({r.get("feature", "不明") for r in records})

    col1, col2 = st.columns([1, 2])
    selected = col1.multiselect("機能で絞り込む", features, default=features)
    keyword = col2.text_input("キーワードで検索", placeholder="タイトル・本文を検索")

    filtered = [
        r
        for r in records
        if r.get("feature") in selected
        and (
            not keyword
            or keyword.lower() in (r.get("title", "") + r.get("output", "")).lower()
        )
    ]

    st.caption(f"{len(filtered)} 件 / 全 {len(records)} 件")
    st.divider()

    for i, record in enumerate(filtered[:100]):
        label = f"[{record.get('feature', '不明')}] {record.get('title', '')[:50]} — {record.get('timestamp', '')}"
        with st.expander(label):
            st.caption(f"モデル: {record.get('model', '不明')}")
            st.markdown(record.get("output", ""))
            st.download_button(
                "⬇️ このテキストを保存",
                record.get("output", ""),
                file_name=f"history_{record.get('timestamp', '').replace(':', '-')}.md",
                mime="text/markdown",
                key=f"hist_dl_{i}",
            )

    if len(filtered) > 100:
        st.caption("※ 表示は新しい100件までです。")

    st.divider()
    with st.expander("⚠️ 履歴の管理"):
        st.download_button(
            "⬇️ 履歴をまとめて書き出す（JSONL）",
            "\n".join(json.dumps(r, ensure_ascii=False) for r in reversed(records)),
            file_name="history_export.jsonl",
            mime="application/jsonl",
        )
        if st.checkbox("すべての履歴を削除する（元に戻せません）"):
            if st.button("履歴を全削除", type="primary"):
                history.clear()
                st.success("履歴を削除しました。")
                st.rerun()
