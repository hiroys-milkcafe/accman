# issue_015: メール管理画面のコンテナエントリ（ou等）の扱い

## 状態（Closed）

## 背景

LDAPメールアカウントツリーの構造:

```
cn=mail_accounts,...
└── ou=<pamuid>,...                          ← コンテナエントリ（PAMユーザごと）
    └── ou=<domain>,...                      ← コンテナエントリ（ドメインごと）
        └── uid=<account>,...               ← メールアカウント（操作対象）
```

メールアカウントのLDAP検索（SUBTREE）はコンテナエントリ（ou=xxx）も結果に含む。
このコンテナエントリが一覧に表示され、誤って編集・削除できる状態だった。

## 問題

1. **削除不可逆**: ouを削除すると配下のメールアカウントがすべて消え、復旧手段がない
2. **編集無意味**: 編集フォームにはuid/mail/userPasswordフィールドがあるが、ouエントリには無関係
3. **一覧での識別不可**: コンテナエントリはuid/mail列が空欄のため何のエントリか判別できない
4. **新規作成時の親OU未指定**: 作成先のOUが指定できず、base_dn直下に誤って作成されていた

## 対応内容

### ① container_attr 設定の追加

- `[template:mail_user]` セクションに `container_attr`（省略時: `ou`）を追加
- DNのRDN部分が `{container_attr}=` で始まるエントリをコンテナとして判定
- ツリー構造に応じて変更可能（例: `dc` など）

### ② 一覧でのコンテナエントリ表示制御

- コンテナエントリは `{container_attr}=値`（例: `ou=alice`、`ou=example.com`）を表示
- コンテナエントリの「編集」「削除」ボタンを非表示（全ユーザ共通）
- 管理者によるコンテナ管理UIは未実装（管理画面設計フェーズで対応）

### ③ 一般ユーザの新規作成時の親OU自動判定

- 入力された `mail` 属性の最初の値の `@` 以降をドメインとして取得
- セッションの `bind_dn` のRDN値をpamuidとして取得
- 親DN = `{container_attr}={domain},{container_attr}={pamuid},{template.base_dn}`
- 親コンテナが存在しない場合: エラーを表示して作成させない（管理者にドメイン作成を依頼）

## 未解決課題（管理画面設計待ち）

### 管理者のコンテナ（ou）追加・削除UI

- 現時点では管理者もコンテナの編集・削除ボタンは非表示
- 管理者がコンテナを管理するUIは別途設計が必要

### 管理者の新規作成時の親OU選択

- 現状、管理者の新規作成は `template.base_dn` 直下に作成する（構造的に誤り）
- 管理者向けの親OU選択UIは管理画面設計フェーズで対応する

## 変更ファイル

- `app/config.py`（`Template.container_attr` フィールド追加、load_configで読み込み）
- `config/accman.ini_sample`（`container_attr` 設定例追加）
- `app/routes/mail.py`（index: コンテナフラグ付与、new: 一般ユーザ親DN導出、session import追加）
- `templates/mail/index.html`（コンテナエントリ表示・ボタン制御、ヘルプ更新）
