# issue_013: PAM・メール管理ルートの is_admin チェック欠落

## 状態（Closed）

## 問題

`pam.edit`・`pam.delete`・`mail` 系ルートに `is_admin` チェックがなく、一般ユーザが直接URLでアクセスできる。

### pam.py の状況

| ルート | is_admin チェック | 一般ユーザの動作 |
|--------|-------------------|-----------------|
| `GET /pam/` | あり | 自分のエントリ編集画面にリダイレクト |
| `GET/POST /pam/new` | あり | 自分のエントリ編集画面にリダイレクト |
| `GET/POST /pam/edit` | **なし** | 任意のDNをパラメータに指定してアクセス可能 |
| `POST /pam/delete` | **なし** | 任意のDNをパラメータに指定して削除リクエスト可能 |

### mail.py の状況

メール管理ルート全体に `is_admin` チェックがない。

## 決定

### アプリ層・ACL層の両方で責任を持つ

ACLだけに依存せず、アプリ層でも悪意のある操作を防ぐ措置を講じる。

### pam.edit

- 一般ユーザが直接アクセスすることを許容する（`/pam/index` からのリダイレクト先として使用されるため）
- is_adminチェックを追加しない
- 実際のデータ保護はLDAP ACL `by self write`（自エントリのみ書込可）に委任

### pam.delete

- 一般ユーザによる削除を **アプリ層で拒否** する
- `is_admin` チェックを追加し、非管理者はメニューページへリダイレクト＋エラーメッセージ表示
- 根拠: 一般ユーザが `/pam/delete` へ直接POSTすることで、自分自身のPAMエントリを削除できてしまう（LDAP ACL `by self write` が技術的に許可するため）

実装済みファイル:
- `app/routes/pam.py`（`delete` ルートに `is_admin` チェック追加）

### mail 系ルート

- 既存実装（is_adminチェックなし）を正とする
- LDAP ACL ルール {2} により、一般ユーザは自分の `ou=<pamuid>` 以下のエントリのみ操作可能
- `mail.delete` についても一般ユーザが直接POSTで自分のメールエントリを削除できるが、これはACLで制御されており許容する（PAMエントリ削除と異なりシステムアクセス不能には直結しない）

## 未解決課題（ACL側）

**OpenLDAP ACL `by self write` の権限範囲が広すぎる問題**

現状のACL（ルール {0}）は `by self write` により、一般ユーザが自分のPAMエントリを削除することを技術的に許可している。アプリ層の `is_admin` チェックでUIからの削除は防いでいるが、ACL側では防いでいない。

今後の対処候補:
- `write` を `mod`（属性変更のみ）に変更し、エントリレベルの add/delete を制限する
- ただしACL変更はLDAPサーバのインフラ設定変更であり、CLAUDE.mdの「ユーザ承認なしに変更禁止」ルールに従い、別途設計・承認のうえで実施する

## 関連ファイル

- `app/routes/pam.py`
- `app/routes/mail.py`
- `docs/requirements/confirmed.md`（一般ユーザのアクセス制御方針）
- `docs/design/confirmed_pam_ui.md`（一般ユーザのリダイレクト設計）
- `docs/design/confirmed_openldap_acl.md`（ACL設計・障害記録）
