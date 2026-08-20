#!/usr/bin/env python3
"""ローカルAIアプリの機械的セキュリティチェック。

目で見て確かめるより、機械が確実に答えられる質問だけをここで片付ける。
「.env は本当に gitignore されているか」「鍵らしい文字列がソースに残っていないか」
「依存はバージョン固定されているか」といった、事実確認で決着する項目である。

判断（深刻度をどう付けるか、直すべきか）はここではやらない。それは人と
モデルの仕事で、脅威モデルによって答えが変わるため。ここは材料を集めるだけ。

秘密情報そのものは絶対に出力しない。見つけた鍵はマスクして、
「どのファイルの何行目に、何文字の鍵らしきものがある」までしか報告しない。
レポートに貼り付けられても事故にならないようにするため。

使い方:
    python scan.py <プロジェクトのパス> [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows のコンソールは既定が cp932 で、日本語の出力が化ける。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 走査対象から外すディレクトリ。仮想環境やキャッシュを掘っても意味がない。
SKIP_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
}

# スキャナ自身が置かれているディレクトリ。検出パターンを書いたコードが
# 検出結果に出てくると、本物の所見が埋もれるので除外する。
SELF_DIR = Path(__file__).resolve().parent.parent


def _is_self(path: Path) -> bool:
    try:
        path.resolve().relative_to(SELF_DIR)
        return True
    except ValueError:
        return False

# ソースとして中身を読むファイル。バイナリを開いて誤検知するのを避ける。
SOURCE_SUFFIXES = {
    ".py", ".toml", ".md", ".txt", ".json", ".yaml", ".yml",
    ".bat", ".sh", ".ps1", ".cfg", ".ini", ".env", ".example",
}

# 鍵らしき文字列のパターン。プロバイダ固有の形が一番当てになる。
SECRET_PATTERNS = [
    ("Google/Gemini APIキー（AIza形式）", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    # AI Studio が今発行するのはこちらの形式。AIza だけ見ていると取り逃がす。
    ("Google/Gemini APIキー（AQ.形式）", re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}")),
    ("OpenAI APIキー", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("Anthropic APIキー", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("AWS アクセスキーID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub トークン", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("秘密鍵ファイルの中身", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# KEY = "..." の形で直書きされた秘密。プレースホルダは除く。
ASSIGNMENT_PATTERN = re.compile(
    r"""(?i)\b(api[_-]?key|secret|token|password|passwd|credential)\b\s*[:=]\s*["']([^"']{12,})["']"""
)

# .env 形式は引用符を使わないので、上のパターンでは拾えない。
# 大文字の環境変数名だけを狙う（大小無視にすると api_key = get_key() のような
# 普通のコードまで鍵と誤認する）。
ENV_ASSIGNMENT_PATTERN = re.compile(
    r"""^\s*(?:export\s+)?([A-Z][A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIALS?))\s*=\s*(\S{12,})\s*$"""
)

# 値がコードなら秘密ではない。関数呼び出しやf文字列を鍵と数えないための目印。
CODE_HINTS = ("(", ")", "{", "}", "f\"", "f'", "os.", "self.", "==")
PLACEHOLDER_HINTS = (
    "your-", "xxx", "<", "dummy", "example", "changeme", "placeholder",
    "todo", "here", "sample", "test-key", "...",
)

# クラウド同期フォルダの目印。ここに置いてあると、ローカル限定のつもりでも外に出る。
SYNC_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive",
                "icloud", "box sync", "pcloud", "nextcloud", "yandexdisk")


def _iter_source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if _is_self(path):
                continue
            if path.suffix.lower() in SOURCE_SUFFIXES or name.startswith(".env"):
                yield path


def _mask(value: str) -> str:
    """鍵を、同一性は分かるが復元はできない形にする。"""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-2:]}（{len(value)}文字）"


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def check_secrets_in_source(root: Path) -> list[dict]:
    """ソースに直書きされた鍵を探す。.env 自体は設計どおりなので別枠で扱う。"""
    findings: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for path in _iter_source_files(root):
        rel = path.relative_to(root).as_posix()
        is_env_file = path.name == ".env" or path.name.startswith(".env.")
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for lineno, line in enumerate(lines, 1):
            # 1行につき1件だけ報告する。同じ鍵が複数のパターンに当たっても
            # 所見が重複して本数が水増しされるだけで、情報は増えないため。
            key = (rel, lineno)
            if key in seen:
                continue

            hit = None
            for label, pattern in SECRET_PATTERNS:
                m = pattern.search(line)
                if m:
                    hit = (label, m.group(0))
                    break

            if hit is None:
                m = ASSIGNMENT_PATTERN.search(line) or ENV_ASSIGNMENT_PATTERN.match(line)
                if m:
                    value = m.group(2).strip("\"'")
                    if any(h in value.lower() for h in PLACEHOLDER_HINTS):
                        continue
                    if any(h in value for h in CODE_HINTS):
                        continue
                    hit = (f"{m.group(1)} に実際の値が入っている", value)

            if hit:
                seen.add(key)
                findings.append({
                    "file": rel, "line": lineno, "kind": hit[0],
                    "masked": _mask(hit[1]), "in_env_file": is_env_file,
                })
    return findings


def check_git(root: Path) -> dict:
    """git 管理下で秘密が追跡されていないかを見る。過去のコミットも見る。"""
    result: dict = {"is_repo": False}
    if _git(root, "rev-parse", "--git-dir") is None:
        return result

    result["is_repo"] = True
    tracked = (_git(root, "ls-files") or "").splitlines()
    result["tracked_secrets"] = [
        f for f in tracked
        if f == ".env" or f.startswith("data/") or f.endswith("secrets.toml")
    ]

    # 今は .gitignore してあっても、過去に一度コミットしていれば履歴に残る。
    historical = []
    for target in (".env", "data/history.jsonl", ".streamlit/secrets.toml"):
        log = _git(root, "log", "--oneline", "--all", "--", target)
        if log and log.strip():
            historical.append({"path": target, "commits": len(log.strip().splitlines())})
    result["historical_secrets"] = historical

    remotes = _git(root, "remote", "-v") or ""
    result["has_remote"] = bool(remotes.strip())
    result["remotes"] = sorted({l.split()[1] for l in remotes.splitlines() if len(l.split()) > 1})
    return result


def check_gitignore(root: Path) -> dict:
    path = root / ".gitignore"
    if not path.exists():
        return {"exists": False, "covers": {}, "raw": ""}
    raw = path.read_text(encoding="utf-8", errors="replace")
    entries = {l.strip().rstrip("/") for l in raw.splitlines() if l.strip() and not l.startswith("#")}
    wanted = {
        ".env": {".env", "*.env", ".env*"},
        "data/": {"data", "data/*", "data/**"},
        ".streamlit/secrets.toml": {".streamlit/secrets.toml", "secrets.toml", ".streamlit"},
    }
    return {
        "exists": True,
        "covers": {name: bool(entries & alts) for name, alts in wanted.items()},
        "raw": raw,
    }


def check_streamlit_config(root: Path) -> dict:
    path = root / ".streamlit" / "config.toml"
    if not path.exists():
        return {"exists": False}
    raw = path.read_text(encoding="utf-8", errors="replace")

    def value_of(key: str) -> str | None:
        m = re.search(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*(?:#.*)?$", raw, re.M)
        return m.group(1).strip().strip('"\'') if m else None

    address = value_of("address")
    return {
        "exists": True,
        "address": address,
        "listens_beyond_localhost": address not in (None, "localhost", "127.0.0.1"),
        "address_unset": address is None,
        "enableXsrfProtection": value_of("enableXsrfProtection"),
        "enableCORS": value_of("enableCORS"),
        "maxUploadSize": value_of("maxUploadSize"),
        "raw": raw,
    }


def check_launchers(root: Path) -> list[dict]:
    """起動スクリプトが config.toml の localhost 指定を上書きしていないか。"""
    hits = []
    for path in list(root.glob("*.bat")) + list(root.glob("*.sh")) + list(root.glob("*.ps1")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        overrides = re.findall(r"--server\.address[= ]\S+|--server\.headless[= ]\S+", raw)
        if overrides:
            hits.append({"file": path.name, "overrides": overrides})
    return hits


def check_dependencies(root: Path) -> dict:
    path = root / "requirements.txt"
    if not path.exists():
        return {"exists": False}
    pinned, unpinned = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        (pinned if "==" in line else unpinned).append(line)
    return {"exists": True, "pinned": pinned, "unpinned": unpinned,
            "has_lockfile": (root / "requirements.lock").exists()}


def check_local_data(root: Path) -> dict:
    data_dir = root / "data"
    info: dict = {"exists": data_dir.exists(), "files": []}
    if not data_dir.exists():
        return info
    for path in sorted(data_dir.rglob("*")):
        if path.is_file():
            entry = {"path": path.relative_to(root).as_posix(),
                     "bytes": path.stat().st_size, "records": None}
            if path.suffix == ".jsonl":
                try:
                    with path.open(encoding="utf-8", errors="replace") as f:
                        entry["records"] = sum(1 for l in f if l.strip())
                except OSError:
                    pass
            info["files"].append(entry)
    return info


def check_sync_folder(root: Path) -> dict:
    """クラウド同期フォルダの中にいないか。localhost限定でも外に出る経路になる。"""
    lowered = str(root.resolve()).lower()
    matched = [m for m in SYNC_MARKERS if m in lowered]
    env_roots = {k: v for k, v in os.environ.items()
                 if k.lower().startswith(("onedrive", "dropbox")) and v}
    return {"path": str(root.resolve()), "matched_markers": matched,
            "in_sync_folder": bool(matched), "sync_env_vars": env_roots}


def check_html_rendering(root: Path) -> list[dict]:
    """モデル出力をHTMLとして描いている箇所。既定はエスケープされるので、明示的な箇所だけ。"""
    pattern = re.compile(r"unsafe_allow_html\s*=\s*True")
    hits = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts) or _is_self(path):
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if pattern.search(line):
                hits.append({"file": path.relative_to(root).as_posix(),
                             "line": lineno, "code": line.strip()})
    return hits


def run(root: Path) -> dict:
    return {
        "root": str(root.resolve()),
        "secrets_in_source": check_secrets_in_source(root),
        "git": check_git(root),
        "gitignore": check_gitignore(root),
        "streamlit_config": check_streamlit_config(root),
        "launchers": check_launchers(root),
        "dependencies": check_dependencies(root),
        "local_data": check_local_data(root),
        "sync_folder": check_sync_folder(root),
        "html_rendering": check_html_rendering(root),
    }


def render(r: dict) -> str:
    out = [f"# 機械チェック結果: {r['root']}", ""]

    out.append("## 秘密情報の直書き")
    secrets = r["secrets_in_source"]
    if not secrets:
        out.append("- ソース内に鍵らしき文字列は見つからなかった")
    for s in secrets:
        where = "（.env なので設計どおり。git管理とファイルの置き場所の方を見ること）" if s["in_env_file"] else "（← ソースに直書き）"
        out.append(f"- {s['file']}:{s['line']} {s['kind']} = {s['masked']} {where}")

    out.append("\n## git")
    g = r["git"]
    if not g["is_repo"]:
        out.append("- git 管理下ではない（＝git経由の流出経路は今のところ無い）")
    else:
        out.append(f"- リモート: {', '.join(g['remotes']) if g['remotes'] else 'なし'}")
        out.append(f"- 追跡されている秘密ファイル: {g['tracked_secrets'] or 'なし'}")
        for h in g["historical_secrets"]:
            out.append(f"- ⚠ 過去のコミットに {h['path']} が {h['commits']} 件残っている")

    out.append("\n## .gitignore")
    gi = r["gitignore"]
    if not gi["exists"]:
        out.append("- .gitignore が無い")
    else:
        for name, ok in gi["covers"].items():
            out.append(f"- {name}: {'カバー済み' if ok else '未カバー'}")

    out.append("\n## Streamlit 設定")
    sc = r["streamlit_config"]
    if not sc["exists"]:
        out.append("- .streamlit/config.toml が無い（既定では全インターフェースで待ち受ける）")
    else:
        out.append(f"- server.address = {sc['address']}"
                   + ("  ← localhost 以外" if sc["listens_beyond_localhost"] else ""))
        for key in ("enableXsrfProtection", "enableCORS", "maxUploadSize"):
            out.append(f"- {key} = {sc[key] if sc[key] is not None else '未設定（既定値）'}")
    for l in r["launchers"]:
        out.append(f"- ⚠ {l['file']} が起動時に上書き: {l['overrides']}")

    out.append("\n## 依存パッケージ")
    d = r["dependencies"]
    if not d["exists"]:
        out.append("- requirements.txt が無い")
    else:
        out.append(f"- バージョン固定済み: {len(d['pinned'])} 件")
        out.append(f"- 未固定: {d['unpinned'] or 'なし'}")
        out.append(f"- ロックファイル: {'あり' if d['has_lockfile'] else 'なし'}")

    out.append("\n## ローカル保存データ")
    ld = r["local_data"]
    if not ld["exists"]:
        out.append("- data/ は未作成")
    for f in ld["files"]:
        rec = f"、{f['records']} 件" if f["records"] is not None else ""
        out.append(f"- {f['path']}: {f['bytes']:,} バイト{rec}（平文）")

    out.append("\n## 置き場所")
    sf = r["sync_folder"]
    out.append(f"- パス: {sf['path']}")
    out.append("- クラウド同期フォルダ内: "
               + (f"はい（{', '.join(sf['matched_markers'])}）" if sf["in_sync_folder"] else "いいえ"))
    if sf["sync_env_vars"]:
        out.append(f"- 同期ツールはこの端末に存在する: {list(sf['sync_env_vars'])}"
                   "（プロジェクト自体は上記のとおり）")

    out.append("\n## HTML描画")
    hits = r["html_rendering"]
    if not hits:
        out.append("- unsafe_allow_html=True の使用なし（Streamlit既定でエスケープされる）")
    for h in hits:
        out.append(f"- {h['file']}:{h['line']} {h['code']}")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".", help="プロジェクトのルート")
    ap.add_argument("--json", action="store_true", help="JSONで出力する")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"ディレクトリが見つからない: {root}", file=sys.stderr)
        return 1

    result = run(root)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
