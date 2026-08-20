# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

Python + Streamlit + Gemini API による個人用AIライティングツール。認証・DBなし。
ブログ執筆、メール返信、要約、校正、リライト、SNS投稿、コピー案出し、翻訳、チャットの9機能＋履歴閲覧を1アプリにまとめている。

## コマンド

すべて仮想環境 `.venv` 前提（PowerShell）。

```powershell
# 依存インストール
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 起動（run.bat のダブルクリックでも同じ）
.\.venv\Scripts\streamlit.exe run app.py

# 動作確認用（ブラウザを開かずに起動）
.\.venv\Scripts\streamlit.exe run app.py --server.headless true
```

`.streamlit/config.toml` で `server.address = "localhost"` を指定しており、LANには公開されない。

### スモークテスト

テストフレームワークは導入していない。UIの回帰確認は Streamlit 標準の `AppTest` で行う。

**重要な落とし穴**: `AppTest.from_function(features.blog.render)` は動かない。
`from_function` は関数のソースだけを抜き出して裸のモジュールで exec するため、
モジュールレベルの import が失われて `NameError: name 'ui' is not defined` になる。
必ず「そのページを呼ぶだけの一時スクリプト」を書き出して `AppTest.from_file` で実行すること。

```python
# 一時ファイルに以下を書き出して AppTest.from_file(...) に渡す
import sys
sys.path.insert(0, r"<プロジェクトの絶対パス>")
from features import blog
blog.render()
```

`at.run()` 後に `at.exception` が空かどうかで判定する。APIキーがなくても描画だけは検証できる。
API呼び出しまで含めて確認したいときは `at.text_area[0].set_value(...)` → `at.button[0].click()` → `at.run()`
とし、`at.error`（UIに出たエラー）と `at.session_state[...]` の両方を見る。

その他 AppTest の注意点:
- `at.session_state` は `dict` ではなく `SafeSessionState`。**`.get()` は使えない**
  （`"key" in at.session_state` で存在確認してから添字アクセスする）。
- `ボタン click → 処理 → st.rerun()` のパターンで処理が二重実行されることはない（検証済み）。

## アーキテクチャ

### 3層構成

```
app.py        ナビゲーション + 全ページ共通サイドバー（モデル/Temperature/思考モード/APIキー）
core/         全機能で共有する土台
features/     1機能 = 1ファイル = render() 関数ひとつ
```

**`core/ui.py` がこの設計の要**。生成・ストリーミング表示・履歴保存・ダウンロード・クリアを
すべて引き受けるため、`features/*.py` に書くのは **入力UIとプロンプト文字列だけ** になる。
新機能を足すときにこの分担を崩さないこと。

### 機能の追加手順

1. `features/新機能.py` に `render()` を定義
2. 入力UIを組み、プロンプトを文字列で組み立てる
3. `ui.generate(state_key, feature=..., title=..., prompt=...)` を呼ぶ
4. その後 `ui.show_result(state_key, filename_stem=...)` を呼ぶ
5. `app.py` の `st.navigation` に `st.Page(新機能.render, title=..., icon=..., url_path=...)` を1行追加

選択肢（トーン・想定読者・言語・モデル）は `config.py` に集約されている。
全機能共通のAI人格は `config.BASE_SYSTEM`（前置きを書かない／不明な事実は創作せず `[要確認]` と書く）。
各ページ固有のプロンプトはこの方針を前提に書く。

### Streamlit の再実行モデルに起因する制約

Streamlit は操作のたびにスクリプトを頭から再実行するため、以下の書き方を守る必要がある。

- **生成結果は必ず `st.session_state` に保存する。**
  `ui.generate()` は「ストリーム表示 → session_state に保存 → 履歴に追記 → `st.rerun()`」の順で動く。
  rerun しないと、ダウンロードボタンを押した次の実行で結果が消える。
- **ウィジェットの key に対して、そのウィジェット生成後に `st.session_state[key] = ...` してはいけない**
  （`StreamlitAPIException` になる）。
  `features/blog.py` の構成案受け渡しがこの回避例：生成結果は別キー `blog_outline_gen` に入れ、
  次の実行の冒頭（`text_area` 生成前）で `pop` して `blog_outline` に移している。
  同種の「生成結果を編集可能な入力欄に流し込む」機能を作るときはこのパターンを踏襲すること。
- `ui.source_text_input()` はファイルアップロード内容をテキストエリアに反映するが、
  同じファイルで再描画されるたびに上書きしないよう `名前:サイズ` の署名で判定している。

### Gemini API まわり（`core/gemini.py`）

- APIキーの解決順は **サイドバー入力 → `.env`（`GEMINI_API_KEY` / `GOOGLE_API_KEY`）→ `st.secrets`**。
  未設定時は `MissingAPIKey` を投げる。
- `genai.Client` は `@st.cache_resource` でキャッシュする（再実行のたびに作り直さない）。
- 生成は常に `generate_content_stream` で、`st.write_stream` に渡せるジェネレータとして返す。
- 例外は UI 側で握りつぶさず、`gemini.friendly_error(e)` に通して対処可能な日本語にしてから `st.error` する。
- チャットは会話履歴を `to_contents()` で `types.Content`（role は `user` / `model`）に変換して毎回全部送る。
  `client.chats` のセッションオブジェクトは使っていない。

#### モデルと思考設定（2026-08 時点で実測済み・推測で書き換えないこと）

- **Gemini 2.5 系は新規ユーザーには提供終了**（`404 ... no longer available to new users`）。
- **Gemini 3 系は `thinking_budget` ではなく `thinking_level`**（`low` / `medium` / `high`）。
  `gemini-3.6-flash`、`gemini-3.5-flash-lite`、`gemini-flash-lite-latest` は `thinking_budget=0` を
  `400 INVALID_ARGUMENT` で拒否する。`minimal` も一部モデルで非対応。
- **Pro（`gemini-3.1-pro-preview` / `gemini-pro-latest`）は無料枠の割当が 0** で常に `429`。
  有料プランが必要。モデル一覧に残してはいるが既定にはしない。
- `gemini-3.7-flash` は `503`（高需要）が頻発する。既定は安定している `gemini-3.5-flash`。
- `gemini-flash-latest` などの alias 系も 503 を返すことがあるため、モデルIDは固定で指定する。
- `stream_generate()` は最大 `_MAX_ATTEMPTS`(=3) 回まで自動リトライする。対象は
  **503/UNAVAILABLE**（待ってやり直し）と **`Thinking level` を含むエラー**（思考指定を外してやり直し）のみ。
  **既に1文字でも yield した後はリトライしない**（画面に途中まで出ているため）。
- `google_genai.models` ロガーは `ERROR` に落としてある。生成のたびに出る
  「AFC は非推奨」警告を消すため。

### 履歴（`core/history.py`）

`data/history.jsonl` に1行1レコードで追記。初回生成時に `data/` ごと自動生成される（gitignore済み）。
壊れた行は読み飛ばす。`overwrite()` は個別削除機能を足すとき用に用意してあるが**現在未使用**。
