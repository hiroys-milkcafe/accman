# issue_006: 編集フォームで任意属性が未設定の場合に IndexError

## 状況

`templates/pam/edit.html` および `templates/mail/edit.html` の単一値フィールドで以下の記述がある。

```jinja2
value="{{ entry.get(attr_def.attr, [''])[0] }}"
```

`ldap_client.get()` は、LDAPエントリに存在しない属性に対してキーを `[]`（空リスト）で返す（except ブランチの `result[attr] = []`）。このとき `entry.get(attr_def.attr, [''])` はデフォルト値でなく `[]` を返すため、`[][0]` が IndexError になり編集画面がエラーで表示できなくなる。

`loginShell` など `required = false` の任意属性が未設定のエントリを開いた場合に発生する。

multi フィールドは `(vals if vals else [''])` で正しく対処済みだが、単一値フィールドのみ漏れている。

## 修正方針

`entry.get(attr_def.attr, [''])[0]` を `(entry.get(attr_def.attr) or [''])[0]` に変更する。`or ['']` により `None` と `[]` の両方を空文字にフォールバックできる。

対象ファイル:
- `templates/pam/edit.html`
- `templates/mail/edit.html`

## 決定（クローズ）

修正方針通りに実装済み。
