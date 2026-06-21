# issue_017: 新規メール作成フォームでエラー後に入力内容が全消えする

## 状態（Closed）

## 問題

`mail/new.html` の新規作成フォームでバリデーションエラーが発生した際、
`render_template('mail/new.html', template=template)` にフォーム送信値を渡していなかった。
テンプレートに前回入力値の表示機構がなく、全フィールドが空にリセットされていた。

## 対応

Flask が Jinja2 テンプレート内で `request` をグローバル変数として提供することを利用し、
テンプレート側で `request.form` から前回送信値を読んで各フィールドに反映する。
ルートハンドラ (`mail.py`) への変更は不要。

復元ルール:
- 単一値フィールド（password 以外）: `request.form.get(attr)` で値を復元
- 複数値フィールド（multi=true, password 以外）: `request.form.getlist(attr)` の非空値を1値1行で展開
- パスワードフィールド: 常に空（セキュリティ上復元しない）
- GET リクエスト時は従来通り空のフォームを表示

変更ファイル: `templates/mail/new.html`
