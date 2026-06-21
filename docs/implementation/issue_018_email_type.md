# issue_018: type = email の新設

## 状態（Closed）

## 背景

メールアドレスを入力する属性に `type = text` を使用していたため、型としての意味（メールアドレス形式）がシステムに伝わらない設計だった。
`mail.py` が属性名 `'mail'` をハードコードして `@` チェックを行っており、属性名が変わると動作しなくなる脆弱性もあった。

データベースで型を設計者が指定するように、メールアドレス入力項目には `email` 型を定義して型の責務として検証を保持すべきとの指摘を受けて対応。

## 対応

`type = email` を新設し、以下の動作を定義する:
- HTML: `<input type="email">` でレンダリング（ブラウザがメールアドレス形式をクライアント検証）
- サーバ: `collect_form_attrs` で `@` 含有を検証。違反時にエラーを追加
- `mail.py new()`: 属性名ハードコードを廃止し、`email` 型属性を動的に検索して使用

## 変更ファイル

- `app/routes/common.py` — `email` 型の `@` 形式検証を追加
- `app/routes/mail.py` — `attrs.get('mail')` ハードコードを廃止、`email` 型属性を動的に探して使用、`@` チェック削除（`collect_form_attrs` に移管）
- `templates/mail/new.html` — input type 決定ロジックを `allowed list` 方式に統一
- `templates/mail/edit.html` — 同上
- `templates/pam/new.html` — 同上
- `templates/pam/edit.html` — 同上
- `config/accman.ini_sample` — `[template:mail_user:mail]` の `type = text` を `type = email` に変更
- `docs/requirements/confirmed.md` — `type` 定義表に `email` を追加
- `docs/design/confirmed_config.md` — `AttributeDef.type` のコメントに `email` を追加
