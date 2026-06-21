# issue_016: 一般ユーザの新規メール作成で multi=false のとき @ チェックが誤って失敗する

## 状態（Closed）

## 問題

`mail.py` の `new()` ルートで、一般ユーザが新規メールエントリを作成する際、
`attrs['mail']` の型を常にリストと決め打ちしていた。

`mail.multi = false` の場合、`collect_form_attrs` は `attrs['mail']` を文字列で返す。
この文字列に対して `mail_vals[0]` を実行すると文字列の先頭1文字（例: `'a'`）が返るため、
`'@' not in 'a'` が True となり、正しいメールアドレスを入力してもエラーと判定されていた。

## 原因

`collect_form_attrs` は `multi` 設定に応じて戻り値の型を変える:
- `multi = true` → リスト
- `multi = false` → 文字列

`new()` はこの違いを考慮せず `mail_vals[0]` を呼んでいた。

## 対応

`attrs['mail']` の型を `isinstance` で判定し、list と str の両方を正しく扱うよう修正。

変更ファイル: `app/routes/mail.py`
