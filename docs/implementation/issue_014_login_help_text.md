# issue_014: login.html の管理者ログイン説明文が誤り

## 状態（Open）

## 問題

`templates/login.html` の `{% block manual %}` 内（33行目）に以下の記述がある:

> 管理者ログイン画面ではパスワードのみ入力します。

しかし実際の管理者ログイン画面（`templates/admin/login.html`）は、commit `46c6fe9` で管理者IDの入力欄が追加されており、現在はID＋パスワードの両方を入力する仕様になっている。

## 関連ドキュメントの不整合

`docs/design/confirmed_help_drawer.md` の「対象画面と内容」テーブルにも誤った記述が残っている:

> | ログイン（管理者） | パスワードのみ入力の説明、一般ユーザログインへの案内 |

こちらも合わせて修正が必要。

## 修正対象

| ファイル | 箇所 | 修正内容 |
|----------|------|---------|
| `templates/login.html` | `{% block manual %}` 33行目 | 「パスワードのみ」→「IDとパスワードを」 |
| `docs/design/confirmed_help_drawer.md` | 「対象画面と内容」テーブル | 管理者ログイン行の説明を修正 |
