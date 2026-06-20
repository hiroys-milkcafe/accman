# issue_011: 一般ユーザログインが失敗する

## 状態（Closed）

一般ユーザのログインおよびログアウトを確認済み。

## 原因と解決

ログに `login failed: uid=dang,cn=accounts,dc=qv,dc=jp ... invalidCredentials` が出力されていた。原因は本番環境の `config/accman.ini` で `[pam] base_dn` に `cn=accounts,dc=qv,dc=jp` を設定していたこと。実際のユーザDNは `uid=dang,cn=users,cn=accounts,dc=qv,dc=jp` であるため、`[pam] base_dn = cn=users,cn=accounts,dc=qv,dc=jp` へ修正することで解決。

## 影響範囲

- `config/accman.ini`（`[pam] base_dn` の値を本番LDAPツリー構造に合わせて設定する）
