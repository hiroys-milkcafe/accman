# OpenLDAP ACL設計 (確定)

## 前提

accmanが正常に動作するには、LDAPサーバ側に以下のACLが設定されている必要がある。
accman自体はACLを管理しない。本ドキュメントはLDAPサーバに設定すべきACLの要件と確認済み構造を記録する。

## LDAPツリー構造

### PAMアカウントツリー

```
cn=users,cn=accounts,dc=qv,dc=jp
└── uid=<uid>,cn=users,cn=accounts,dc=qv,dc=jp   （PAMユーザエントリ）
```

### メールアカウントツリー

```
cn=mail_accounts,dc=qv,dc=jp
└── ou=<pamuid>,cn=mail_accounts,dc=qv,dc=jp          （PAMユーザごとのOU）
    └── ou=<domain>,ou=<pamuid>,cn=mail_accounts,dc=qv,dc=jp  （ドメインごとのOU）
        └── uid=<email>,ou=<domain>,ou=<pamuid>,cn=mail_accounts,dc=qv,dc=jp  （メールアカウント）
```

`ou=<pamuid>` の値は対応するPAMユーザの uid と一致する。
一般ユーザは自分のuidと同じ名前の `ou=<pamuid>` 以下のエントリにのみアクセスできる。

## 確認済みACL（mdb database）

mta01サーバのOpenLDAPで確認・適用されているACL（`olcDatabase={2}mdb,cn=config`）:

### ルール {0} — PAMアカウントツリー全体

```
to dn.subtree="cn=users,cn=accounts,dc=qv,dc=jp"
  by self write
  by dn="cn=admin,dc=qv,dc=jp" write
  by users read
  by * none
```

- PAMユーザは自分のエントリを書き換えられる（パスワード変更）
- 管理者（rootDN）は全エントリを書き換えられる
- ログイン済みユーザは読み取りできる

### ルール {1} — メールアカウントツリーのベースエントリ

```
to dn.base="cn=mail_accounts,dc=qv,dc=jp"
  by users search
  by * none
```

- ログイン済みユーザがメールアカウントツリーのサブツリー検索を開始するために必要
- ベースエントリ自体への `search` アクセスがないとLDAPのSUBTREE検索が失敗する

### ルール {2} — メールアカウントエントリ（一般ユーザの自己管理）

```
to dn.regex="^(.*,)?ou=([^,]+),cn=mail_accounts,dc=qv,dc=jp$"
  by dn.regex="^uid=$2,cn=users,cn=accounts,dc=qv,dc=jp$" write
  by * none
```

- `$2` にはDNの `cn=mail_accounts,dc=qv,dc=jp` 直上の `ou=` の値が入る（= PAMユーザのuid）
- そのuidに対応するPAMユーザが、自分の `ou=<uid>` 以下のメールエントリすべてに対してwrite権限を持つ
- 正規表現 `(.*,)?` により `ou=<domain>,ou=<pamuid>,...` と任意の深さのエントリに適合する

## Postfix / Dovecotのバインド

PostfixおよびDovecotはrootDN（`cn=admin,dc=qv,dc=jp`）でバインドする設定のため、OpenLDAPのACLをバイパスする。これらのサービス向けに個別のACLルールは不要。

## 適用コマンド（参考）

ACLを追加する場合は `replace:` ではなく `add:` を使用する。`replace:` はデータベース全体のolcAccessを上書きするため、既存ルールが消滅する。

```ldif
dn: olcDatabase={2}mdb,cn=config
changetype: modify
add: olcAccess
olcAccess: {N}to ...
```

確認コマンド:

```sh
ldapsearch -Y EXTERNAL -H ldapi:/// -b "olcDatabase={2}mdb,cn=config" olcAccess
```

## 障害記録（2026年6月）

前スレッドのClaude Codeセッションが `replace: olcAccess` を使って部分的なLDIFをLDAPサーバに適用した。この操作によりACLルール {1} および {2} が消滅し、一般ユーザのメール管理画面が完全に閲覧不能になった。

原因:
1. Claude Codeがユーザの承認なしにACLを変更した
2. 変更の意図・内容・経緯がドキュメントに記録されなかった
3. `replace:` と `add:` の違いを把握せずにLDIFを生成した

この障害を受け、CLAUDE.mdにインフラ設定変更の禁止ルールを追加した（「設定・運用への影響がある変更のルール」参照）。
