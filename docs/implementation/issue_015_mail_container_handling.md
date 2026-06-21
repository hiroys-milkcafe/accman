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

### ④ display_only 属性設定の追加（mail 属性）

- `[template:mail_user:mail]` に `display_only = true` を設定
- 一般ユーザの編集画面では `mail` 属性を読み取り専用テキストで表示（フォーム送信時も変更を送らない）
- 管理者は通常通り編集可能
- 理由: 一般ユーザが他ユーザ宛メールのアドレスを自アカウントに追加できてしまうリスクを防ぐ

### ⑤ 一覧のDN階層順グルーピング表示

- エントリを `_entry_sort_key(dn, base_dn)` でソート（base_dn からの相対パスを親→子順のタプルで比較）
- 各エントリに `_depth`（= タプル長 - 1）を付与し、第1セルに `padding-left: calc(0.8rem + {depth * 1.5}rem)` を適用
- コンテナ行に `class="mail-group-row"` を付与（背景色 `#edf2f7`、太字）
- base_dn エントリ自体は検索結果からフィルタ除外
- **コンテナ行のcolspan**: `colspan="{{ display_attrs|length + 1 }}"` で操作列まで含む1セルにする。操作列を空の `<td class="actions">` として別セルにすると `display: flex` の空セル高さ不一致により行区切り線がずれるため

## 変更ファイル

- `app/config.py`（`AttributeDef.display_only` フィールド追加、`Template.container_attr` フィールド追加、load_configで読み込み）
- `config/accman.ini_sample`（`container_attr`・`display_only` 設定例追加）
- `app/routes/mail.py`（index: 階層ソート・depthフラグ付与・コンテナフラグ付与・base_dnフィルタ、new: 一般ユーザ親DN導出・session import、edit: skip_attrs による display_only スキップ）
- `app/routes/common.py`（`collect_form_attrs` に `skip_attrs` パラメータ追加）
- `templates/mail/index.html`（階層インデント・コンテナ行スタイル・ボタン制御・colspan修正・ヘルプ更新）
- `templates/mail/edit.html`（display_only 属性の読み取り専用表示）
- `templates/pam/edit.html`（display_only 属性の読み取り専用表示）
- `static/css/style.css`（`.mail-group-row`・`.field-display` クラス追加）
- `docs/design/confirmed_config.md`（AttributeDef・Template データクラス更新）
- `docs/design/confirmed_mail_ui.md`（コンテナ処理・display_only・階層グルーピング・親OU自動判定を追記）
