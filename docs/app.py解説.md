# `app.py` 解説

AI Writing Studio の入口ファイル。全126行を、上から順に読み解きます。

---

## 0. 先に：このファイルの起動方法

冒頭で試された

```powershell
& 'c:\...\02.Create-AI\app.py'
```

では動きません。これは「app.py をダブルクリックで開く」のと同じ意味になり、Pythonのプログラムとしては実行されないためです。

さらに、たとえ `python app.py` としても正しく動きません。**Streamlitアプリは専用のコマンドで起動する必要があります。**

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

理由は、Streamlitが単なるライブラリではなく「**Webサーバーを立ち上げて、その中で app.py を繰り返し実行する仕組み**」だからです。`streamlit run` はそのサーバーを起動するコマンドで、`st.title()` などはサーバーの中で実行されて初めてブラウザに描画されます。サーバーの外で実行しても、何も表示されずに終わります。

---

## 1. このファイルの役割

`app.py` がやっているのは、**3つだけ**です。

| 役割 | 該当箇所 |
|---|---|
| ページ全体の設定（タブ名・アイコン・レイアウト） | 23〜28行目 |
| 全ページ共通のサイドバーを描く | 54〜92行目 |
| 左メニューを組み立て、選ばれたページを実行する | 95〜121行目 |

**文章生成のロジックは1行も入っていません。** それらは `core/` と `features/` にあります。`app.py` は交通整理役に徹しています。

---

## 2. 全体の地図

```
 1〜 4行   docstring（ファイルの説明）
 6〜21行   import（部品の読み込み）
23〜28行   st.set_page_config（ページ全体の設定）
31〜51行   def home()      ← トップページの中身
54〜92行   def sidebar()   ← 共通サイドバーの中身
95〜121行  def main()      ← 左メニューの組み立て
124〜125行 if __name__ == "__main__": main()
```

`def` は「関数を**定義する**」だけで、その場では実行されません。実際に動き出すのは最後の2行です。

---

## 3. ブロックごとの解説

### 1〜4行目：docstring

```python
"""AI Writing Studio — Streamlit + Gemini API による個人用ライティングツール。

起動: streamlit run app.py
"""
```

ファイルの先頭に置いた文字列は **docstring** と呼ばれ、そのファイルの説明として扱われます。`#` のコメントと違い、プログラムから `app.__doc__` として読み出せます。

ここに起動コマンドを書いているのは、**半年後の自分が最初に目にする場所だから**です。

---

### 6〜21行目：import

```python
import streamlit as st

import config
from core import gemini
from features import (
    blog,
    chat,
    history_view,
    ...
)
```

3つのグループに分かれています。この並び順はPythonの慣習です。

| グループ | 内容 |
|---|---|
| 外部ライブラリ | `streamlit`（`as st` で短い別名を付ける。慣例） |
| 自作の設定 | `config`（同じフォルダにある `config.py`） |
| 自作の部品 | `core` / `features` フォルダの中身 |

`from features import (blog, chat, ...)` は、`features` フォルダの中の `blog.py`、`chat.py`… をまとめて読み込む書き方です。カッコで囲むと複数行に分けて書けます。

> **なぜ `features/__init__.py`（中身は空）が必要か**
> Pythonは「`__init__.py` があるフォルダ」をパッケージとして扱います。空でも置いておくことで `from features import blog` が成立します。

---

### 23〜28行目：ページ全体の設定

```python
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)
```

| 引数 | 効果 |
|---|---|
| `page_title` | ブラウザのタブに出る文字 |
| `page_icon` | タブのアイコン（絵文字が使える） |
| `layout="centered"` | 本文を中央寄せの読みやすい幅に。`"wide"` なら画面いっぱい |
| `initial_sidebar_state="expanded"` | 最初からサイドバーを開いた状態にする |

**重要なルール：`st.set_page_config()` は、他のどの `st.〜` よりも先に呼ばなければなりません。** 順番を間違えると `StreamlitAPIException` で落ちます。関数の中ではなくファイルの上部に直接書いてあるのはそのためです。

値を直書きせず `config.APP_TITLE` を参照しているのは、アプリ名を変えたいときに `config.py` の1か所だけ直せば済むようにするためです。

---

### 31〜51行目：`home()` — トップページ

```python
def home() -> None:
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.caption("書く・直す・まとめる。...")
    st.divider()
```

| 書き方 | 意味 |
|---|---|
| `-> None` | 「この関数は何も返さない」という**注釈**。Pythonは強制しないが、読む人と補完機能への説明になる |
| `f"{...}"` | f-string。`{}` の中に変数を埋め込める |
| `st.title` / `st.caption` / `st.divider` | 大見出し / 小さな灰色文字 / 横線 |

```python
    tools = [
        ("📝", "ブログ記事執筆", "構成案から本文まで、2ステップで記事を書き上げる"),
        ("📧", "メール返信作成", "受信メールを貼るだけで返信の下書きをつくる"),
        ...
    ]
    for icon, name, description in tools:
        st.markdown(f"**{icon} {name}** — {description}")
```

`tools` は**タプルのリスト**です。`("📝", "ブログ記事執筆", "…")` のように3つの値が1組になっています。

`for icon, name, description in tools:` の部分が肝で、これは**アンパック**という書き方です。1周ごとに3つの値が自動的に3つの変数へ割り振られます。

```python
# アンパックを使わないと、こう書くことになる
for tool in tools:
    st.markdown(f"**{tool[0]} {tool[1]}** — {tool[2]}")
```

`tool[0]` より `icon` の方が、何を指しているか一目で分かります。

**なぜリストにするのか：** 9個の `st.markdown(...)` をベタ書きしても同じ表示になります。しかしリストにしておけば、後で「説明文だけ小さく表示したい」となったとき、**ループの1行を直すだけで9項目すべてに反映**されます。データと表示方法を分けておく、という考え方です。

---

### 54〜92行目：`sidebar()` — 共通の設定パネル

ここがこのファイルで一番読みごたえのある部分です。

```python
def sidebar() -> None:
    """全ページ共通の設定パネル。"""
    with st.sidebar:
```

`with st.sidebar:` は「**このブロックの中で書いた `st.〜` は、本文ではなくサイドバーに描画する**」という指定です。インデントが下がっている間ずっと有効になります。

```python
        with st.expander("⚙️ 生成設定", expanded=False):
```

`st.expander` は折りたたみパネル。`expanded=False` なので初期状態は閉じています。設定は毎回触るものではないので、普段は畳んでおく判断です。

#### モデル選択：表示名とIDの変換

```python
            label = st.selectbox("モデル", list(config.MODELS.keys()), key="model_label")
            st.session_state["model"] = config.MODELS[label]
```

`config.MODELS` は**辞書**で、こうなっています。

```python
MODELS = {
    "Gemini 3.5 Flash（安定・おすすめ）": "gemini-3.5-flash",   # 表示名 : モデルID
    "Gemini 3.7 Flash（最新・混雑しやすい）": "gemini-3.7-flash",
    ...
}
```

- `list(config.MODELS.keys())` で**表示名だけ**を取り出し、プルダウンの選択肢にする
- 選ばれた表示名（`label`）を `config.MODELS[label]` に渡すと、**APIに送るモデルID**が得られる
- それを `st.session_state["model"]` に保存する

人間には「Gemini 3.5 Flash（安定・おすすめ）」を見せ、APIには `gemini-3.5-flash` を渡す。この2つを辞書1つで橋渡ししています。

> **`st.session_state` とは**
> Streamlitは操作のたびにファイルを頭から再実行するため、普通の変数は毎回リセットされます。`st.session_state` は**その再実行をまたいで値を保持する専用の入れ物**です。ブラウザを閉じるまで残ります。
> ここに保存した値を、各機能ページが `ui.settings()` 経由で読み取ります。

#### `key` を付けると何が起きるか

```python
            st.slider(
                "創造性（Temperature）",
                min_value=0.0, max_value=2.0, value=0.7, step=0.1,
                key="temperature",
                help="低いほど堅実で安定、高いほど自由で意外性のある文章になります。",
            )
```

このスライダーは**戻り値を変数で受け取っていません**。`key="temperature"` を付けると、Streamlitが選択値を自動的に `st.session_state["temperature"]` へ入れてくれるからです。

`help=` に文字列を渡すと、ラベルの横に「?」アイコンが出て、ホバーで説明が表示されます。

> **注意すべき落とし穴**
> `key="temperature"` を指定したウィジェットに対して、**ウィジェットを作った後に** `st.session_state["temperature"] = 0.5` と代入すると例外になります。だからモデル選択では、ウィジェットの `key` は `"model_label"` にして、変換後の値は別名の `"model"` に入れています。この使い分けは意図的なものです。

#### 思考レベル

```python
            level_label = st.selectbox(
                "思考レベル",
                list(config.THINKING_LEVELS.keys()),
                index=1,
                help="高いほどじっくり考えて品質が上がり、低いほど速く安くなります。",
            )
            st.session_state["thinking_level"] = config.THINKING_LEVELS[level_label]
```

モデル選択と同じ「表示名 → 実際の値」の変換パターンです。`index=1` は**初期選択を2番目にする**指定（0から数えるため）。選択肢は「低（速い）／中（標準）／高（じっくり考える）」なので、既定は「中（標準）」になります。

> こちらの `selectbox` には `key=` が付いていません。動作に違いはありません（`key` がなくてもStreamlitは選択状態を保持します）が、**モデル選択と書き方が揃っていない**のは事実です。統一するなら `key="thinking_label"` を足すのが自然です。

#### APIキー欄：開くかどうかを状況で変える

```python
        with st.expander("🔑 APIキー", expanded=not gemini.resolve_api_key()):
```

ここが小さな工夫です。`gemini.resolve_api_key()` はキーが見つかれば文字列を、なければ `None` を返します。

| キーの状態 | `resolve_api_key()` | `not ...` | 結果 |
|---|---|---|---|
| 設定済み | 文字列（真） | `False` | 閉じたまま（邪魔しない） |
| 未設定 | `None`（偽） | `True` | **自動で開く**（すぐ入力できる） |

Pythonでは空でない文字列は真、`None` は偽として扱われるため、`not` を付けるだけでこの出し分けができます。

```python
            st.text_input(
                "Gemini APIキー",
                type="password",
                key="api_key_input",
                help=".env に GEMINI_API_KEY を書いておけば、毎回の入力は不要です。",
            )
            st.caption("[Google AI Studio で取得](https://aistudio.google.com/apikey)")
```

`type="password"` で入力文字が `●●●●` に伏せられます。`key="api_key_input"` に入った値を、`core/gemini.py` の `resolve_api_key()` が最優先で読みに行きます。

`st.caption` の中の `[表示文字](URL)` はMarkdown記法で、リンクになります。

#### 状態表示

```python
        if gemini.resolve_api_key():
            st.success("APIキー: 設定済み", icon="✅")
        else:
            st.error("APIキーが未設定です", icon="⚠️")
```

サイドバーの一番下に、緑または赤のバッジを出します。**生成ボタンを押して初めて失敗に気づく**という事態を避けるため、常時見える位置に置いています。

---

### 95〜121行目：`main()` — 左メニューの組み立て

```python
def main() -> None:
    sidebar()

    navigation = st.navigation({...})
    navigation.run()
```

**`sidebar()` を `navigation.run()` より先に呼んでいるのが重要です。** `app.py` は毎回頭から実行されるので、先に共通サイドバーを描いてから各ページを描く、という順番になります。これにより、どのページを開いてもサイドバーが表示されます。

```python
    navigation = st.navigation(
        {
            "ホーム": [
                st.Page(home, title="ホーム", icon="🏠", url_path="home", default=True),
            ],
            "書く": [
                st.Page(blog.render, title="ブログ記事", icon="📝", url_path="blog"),
                st.Page(mail.render, title="メール返信", icon="📧", url_path="mail"),
                ...
            ],
            "直す・まとめる": [...],
            "その他": [...],
        }
    )
```

`st.navigation` に**辞書**を渡すと、**キーがメニューの見出し**になり、値のリストがその下の項目になります。左メニューに「ホーム／書く／直す・まとめる／その他」という区切りが出るのはこの構造によるものです。

#### `st.Page(blog.render, ...)` — カッコを付けない理由

ここが初学者のつまずきどころです。

```python
st.Page(blog.render, ...)    # ⭕ 正しい：関数「そのもの」を渡す
st.Page(blog.render(), ...)  # ❌ 間違い：今すぐ実行して、その結果を渡す
```

Pythonでは、関数名にカッコを付けると**その場で実行**されます。カッコなしの `blog.render` は「実行せずに、関数という部品を手渡す」という意味になります。

`st.Page` に渡したいのは「**ユーザーがそのメニューを選んだときに実行してほしい処理**」であって、今すぐの実行結果ではありません。だからカッコを付けません。

| 引数 | 意味 |
|---|---|
| `title` | 左メニューに表示される名前 |
| `icon` | その横のアイコン |
| `url_path` | URLの末尾。`url_path="blog"` なら `localhost:8501/blog` で直接開ける |
| `default=True` | 最初に開くページ。全体で1つだけ指定する |

```python
    navigation.run()
```

**この1行で、ユーザーが選んでいるページの関数が実際に呼ばれます。** 「ブログ記事」が選ばれていれば `blog.render()` が、ホームなら `home()` が実行されます。

---

### 124〜125行目：`if __name__ == "__main__"`

```python
if __name__ == "__main__":
    main()
```

`__name__` はPythonが自動で用意する変数で、値は状況によって変わります。

| 状況 | `__name__` の値 |
|---|---|
| そのファイルが**直接実行**された | `"__main__"` |
| 他のファイルから `import` された | `"app"`（ファイル名） |

つまりこの2行は「**このファイルが直接実行されたときだけ `main()` を動かす**」という意味です。

`streamlit run app.py` で起動すると、Streamlitは app.py を「直接実行」の扱いで動かすため `__name__` が `"__main__"` になり、`main()` が呼ばれます。

**何のためにあるのか：** もし将来 `import app` として別のファイルから部品だけ借りたくなったとき、この if がなければ import した瞬間にアプリ全体が起動してしまいます。それを防ぐ安全装置です。Pythonのほぼ全てのスクリプトで見かける定型句なので、覚えてしまって構いません。

---

## 4. ボタンを押したとき、何が起きるか

Streamlitで最も理解しづらいのが**再実行モデル**です。「ブログ記事」ページで生成ボタンを押したときの流れを追います。

```
① ブラウザでボタンが押される
        ↓
② app.py が【1行目から】もう一度まるごと実行される
        ↓
③ st.set_page_config() が走る
        ↓
④ main() → sidebar() が走り、サイドバーが描き直される
   （選択中のモデル等は st.session_state から復元される）
        ↓
⑤ navigation.run() → blog.render() が走る
        ↓
⑥ render() の中で「ボタンが押された」と判定され、生成処理が動く
        ↓
⑦ 結果を st.session_state に保存し、st.rerun() でもう一度②へ
        ↓
⑧ 今度はボタンが押されていない状態で実行され、
   保存済みの結果が画面に表示される
```

**ポイントは②です。** 「押された部分だけ動く」のではなく、**毎回ファイル全体が上から下まで再実行されます。**

だからこそ、

- 普通の変数では値が残らない → **`st.session_state` に入れる**
- `st.set_page_config()` は毎回呼ばれる → **必ず一番上に置く**
- `sidebar()` も毎回呼ばれる → **だから全ページに表示される**

という設計になっています。一見わざわざに見える書き方には、すべてこの再実行モデルという理由があります。

---

## 5. よくある疑問

**Q. `st.` って何の略？**
`import streamlit as st` で付けた別名です。`streamlit.title()` と書いても同じですが、Streamlitの世界では `st` が慣例として定着しています。

**Q. `home()` や `sidebar()` はどこで呼ばれている？**
`home()` は `st.Page(home, ...)` として登録され、`navigation.run()` が呼び出します。`sidebar()` は `main()` の1行目で直接呼ばれます。

**Q. `-> None` を消したら動かなくなる？**
動きます。型注釈は人間とエディタのための説明で、Pythonの実行には影響しません。

**Q. 9つの機能のコードはどこ？**
`features/` フォルダです。`app.py` はメニューに登録しているだけで、中身は持っていません。

---

## 6. 手を入れるとき

| やりたいこと | 触る場所 |
|---|---|
| アプリ名・アイコンを変える | `config.py` の `APP_TITLE` / `APP_ICON` |
| 使うモデルを増減する | `config.py` の `MODELS` |
| メニューの並び順・グループを変える | `app.py` の `st.navigation({...})` |
| トップページの説明文を直す | `app.py` の `home()` 内の `tools` |
| 新しい機能を追加する | `features/新機能.py` を作り、`st.navigation` に `st.Page` を1行追加 |
| 生成の共通処理を変える | `core/ui.py`（`app.py` ではない） |

`app.py` に手を入れる場面は、実はそう多くありません。**機能を足すときに `st.Page` を1行増やす**、これがほとんどです。
