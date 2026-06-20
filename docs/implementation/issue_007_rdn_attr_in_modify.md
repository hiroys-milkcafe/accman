# issue_007: 編集時に RDN 属性が MODIFY_REPLACE に含まれる

## 状況

`app/routes/pam.py` および `app/routes/mail.py` の編集POST処理で、`_collect_form_attrs` はテンプレートの全属性（RDN属性を含む）を収集して `modify()` に渡す。RDN属性（例: PAMユーザの `uid`）は DN の構成要素であり、値が変わらなくても `MODIFY_REPLACE` を拒否するLDAPサーバがある。

また編集フォームでRDN属性が通常の編集可能フィールドとして表示されるため、ユーザが変更しようとすると LDAP エラーになる。ヘルプには「編集画面では変更できません」と記載されているが、フォーム自体は入力を受け付ける状態になっている。

## 修正方針

- サーバ側: edit POST で `modify()` を呼ぶ前に `changes.pop(template.rdn_attr, None)` で RDN 属性を除外する
- テンプレート側: 編集フォームの RDN 属性フィールドに `readonly` を付与してユーザの変更を防ぐ

対象ファイル:
- `app/routes/pam.py`
- `app/routes/mail.py`
- `templates/pam/edit.html`
- `templates/mail/edit.html`

## 決定（クローズ）

修正方針通りに実装済み。
