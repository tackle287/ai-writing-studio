"""Gemini API の薄いラッパー。ストリーミング生成だけを提供する。"""

from __future__ import annotations

import logging
import os
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

import config

load_dotenv()

# ツールを使わない普通の生成でも毎回出る「AFCは非推奨」警告を黙らせる
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

# 混雑（503）や思考レベル非対応のときに何回までやり直すか
_MAX_ATTEMPTS = 3


class MissingAPIKey(RuntimeError):
    """APIキーが見つからないときに投げる。"""


def resolve_api_key() -> str | None:
    """セッション入力 → .env → st.secrets の順にAPIキーを探す。"""
    key = st.session_state.get("api_key_input")
    if key:
        return key.strip()

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key.strip()

    try:
        return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def _get_client(api_key: str) -> genai.Client:
    """APIキーごとにクライアントを使い回す（再実行のたびに作り直さない）。"""
    return genai.Client(api_key=api_key)


def _build_config(
    system_instruction: str | None,
    temperature: float,
    thinking_level: str | None,
) -> types.GenerateContentConfig:
    kwargs: dict = {"temperature": temperature}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if thinking_level:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
    return types.GenerateContentConfig(**kwargs)


def _iter_text(client, model, contents, cfg):
    for chunk in client.models.generate_content_stream(
        model=model, contents=contents, config=cfg
    ):
        if chunk.text:
            yield chunk.text


def stream_generate(
    contents,
    *,
    system_instruction: str | None = None,
    model: str = config.DEFAULT_MODEL,
    temperature: float = 0.7,
    thinking_level: str | None = config.DEFAULT_THINKING_LEVEL,
):
    """テキストを少しずつ yield するジェネレータ。st.write_stream にそのまま渡せる。"""
    api_key = resolve_api_key()
    if not api_key:
        raise MissingAPIKey(
            "Gemini APIキーが設定されていません。サイドバーから入力するか、"
            ".env に GEMINI_API_KEY を設定してください。"
        )

    client = _get_client(api_key)
    cfg = _build_config(system_instruction, temperature, thinking_level)

    for attempt in range(_MAX_ATTEMPTS):
        produced = False
        try:
            for text in _iter_text(client, model, contents, cfg):
                produced = True
                yield text
            return
        except Exception as e:
            # 出力が始まった後はやり直せない（途中まで表示済みのため）
            if produced or attempt == _MAX_ATTEMPTS - 1:
                raise

            message = str(e)
            # モデルによっては指定した思考レベルを受け付けない → 指定を外してやり直す
            if "Thinking level" in message:
                cfg = _build_config(system_instruction, temperature, None)
                continue
            # 混雑（503）は一時的なので、少し待ってやり直す
            if any(marker in message for marker in ("503", "UNAVAILABLE")):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise


def friendly_error(e: Exception) -> str:
    """APIエラーを、対処が分かる日本語に言い換える。"""
    message = str(e)

    if isinstance(e, MissingAPIKey):
        return message
    if "API_KEY_INVALID" in message or "API key not valid" in message:
        return "APIキーが無効です。.env の GEMINI_API_KEY を確認してください。"
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return (
            "利用上限に達しました。無料枠の1日/1分あたりの上限を超えたか、短時間に送りすぎています。"
            "少し待つか、サイドバーで軽いモデルに切り替えてください。"
            "（Proモデルは無料枠の割当が0のため、有料プランが必要です）"
        )
    if "no longer available" in message:
        return "このモデルは提供が終了しています。サイドバーから別のモデルを選んでください。"
    if "UNAVAILABLE" in message or "503" in message:
        return "モデルが混雑しています。少し待って再実行するか、別のモデルを選んでください。"
    if "NOT_FOUND" in message or "404" in message:
        return "モデルが見つかりません。サイドバーから別のモデルを選んでください。"

    return f"生成に失敗しました: {e}"


def to_contents(messages: list[dict]) -> list[types.Content]:
    """[{"role": "user"/"assistant", "content": "..."}] を API 形式に変換する。"""
    return [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in messages
    ]
