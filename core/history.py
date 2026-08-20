"""生成履歴をローカルのJSONLに追記して保存する。"""

from __future__ import annotations

import json
from datetime import datetime

import config


def _ensure_file() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.touch(exist_ok=True)


def add(feature: str, title: str, output: str, model: str) -> None:
    _ensure_file()
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "feature": feature,
        "title": title,
        "model": model,
        "output": output,
    }
    with config.HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load() -> list[dict]:
    """新しい順に返す。壊れた行は黙って読み飛ばす。"""
    if not config.HISTORY_FILE.exists():
        return []

    records = []
    with config.HISTORY_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(records))


def overwrite(records: list[dict]) -> None:
    """load() が返した新しい順のリストを受け取り、古い順に書き戻す。"""
    _ensure_file()
    with config.HISTORY_FILE.open("w", encoding="utf-8") as f:
        for record in reversed(records):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def clear() -> None:
    if config.HISTORY_FILE.exists():
        config.HISTORY_FILE.unlink()
