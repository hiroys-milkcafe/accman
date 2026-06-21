# 確定要件

## プロジェクト概要

LDAPを通じたアカウント管理を行うWebベースの操作UIを構築する。

---

## 管理対象

### 1. PAMアカウント管理

- ユーザアカウントとグループの管理
- sudo可能なユーザ／グループの管理（sudoer）

### 2. メールアカウント管理

- MTA（メール転送エージェント）およびIMAP/POPサーバがLDAPを通じて利用する認証情報・スプール情報のLDAPエントリ管理
- 特定のMTA実装（Postfix/Dovecot等）に依存しない設計とする

---

## ログイン種別

| 種別 | 説明 |
|------|------|
| 管理者 | RootDNでログイン。全PAMアカウント・全メールツリーの管理が可能 |
| 一般ユーザ | PAMユーザのBINDでログイン。自分のPAMアカウントの編集と、LDAPサーバのACLで許可されたメールツリーのメンテナンスが可能 |

---

## 認証フロー

### 管理者ログイン

1. 管理者のBIND DNとIDはバックエンド設定ファイルに記載する
2. `/admin/login` でID＋パスワードを入力する
3. 入力IDを設定ファイルの `admin.id` と照合する（不一致ならエラー）
4. 設定ファイルのRootDN＋入力パスワードでLDAPにBINDする
5. BIND成功後、管理者セッションとして保持する

### 一般ユーザログイン

1. ユーザはWebUIでuid＋パスワードのみ入力する（DNの入力は不要）
2. サーバ側がBIND DNを組み立てる（例: `uid={uid},{pam_base_dn}`）
3. 組み立てたDN＋パスワードでLDAPにBINDする
4. BIND成功後、資格情報をセッションに保持し、以降のLDAP操作に使用する
5. アクセス制御はLDAPサーバのACLに委ねる（アプリ層では独自ACLを実装しない）

---

## LDAP接続設定

- 対象LDAPサーバは特定しない（クライアントとして汎用的に動作する）
- 以下をアプリの設定として定義できるようにする
  - LDAPサーバのホスト／ポート
  - 管理者（RootDN）のBIND DN
  - 一般ユーザログイン用BIND DN組み立てに使うベースDN（`[pam] base_dn`）
  - テンプレートごとのエントリ格納先（テンプレートIDをキーとして `[pam]`/`[mail]` セクションに設定する。[設定ローダー設計](../design/confirmed_config.md) 参照）

---

## スキーマ・エントリテンプレート

- 特定のObjectClassをコードにハードコードしない
- 「PAMユーザ」「PAMグループ」「メールユーザ」等のエントリ種別ごとに、使用するObjectClassと属性の一覧を設定ファイルで定義する（テンプレート方式）
- UIはテンプレートに基づいてフォームを構成する

---

## 動作環境

- OS: AlmaLinux 9
- Python: 3.9 以上

---

## 技術スタック

| 層 | 採用技術 |
|----|----------|
| フロントエンドプロキシ | NGINX（リバースプロキシ） |
| バックエンド | Python + Jinja2テンプレート（SSR） |
| JavaScript | 最小限（SPAフレームワークは使用しない） |

採用理由: 社内運用ツールとして、デプロイ・バージョンアップの運用負荷を最小化するため、npm・ビルドパイプライン・SPAフレームワークを使用しない。

---

## 設定ファイルスキーマ

形式: INI  
配置場所: `config/accman.ini`（パスは環境変数 `ACCMAN_CONFIG` で上書き可能）  
パスワード類は設定ファイルに直書きせず、環境変数で渡す。

### 全体構造

```ini
[ldap]
host = ldap.example.com
port = 636
tls = true
ca_cert = /etc/ssl/certs/ca.pem  ; 省略時はシステムの証明書ストアを使用

[admin]
id = admin                              ; ログイン画面で入力するID。BIND DNとは独立して照合する
bind_dn = cn=admin,dc=example,dc=com   ; 管理者のBIND DN

[pam]
base_dn = ou=people,dc=example,dc=com  ; 一般ユーザログイン用（BIND DN組み立て専用）
pam_user = ou=people,dc=example,dc=com ; テンプレートIDをキーにしたエントリ格納先
pam_group = ou=groups,dc=example,dc=com
sudoer = ou=sudoers,dc=example,dc=com

[mail]
mail_user = ou=mail,dc=example,dc=com  ; テンプレートIDをキーにしたエントリ格納先

[session]
admin_timeout = 3600     ; 管理者セッションのタイムアウト秒数
user_timeout = 28800     ; 一般ユーザセッションのタイムアウト秒数

[log]
syslog_enabled = false   ; syslogへの追加出力を有効化する（true/false）
syslog_facility = local3 ; syslogのfacility

[template:pam_user]
name = PAMユーザ
scope = pam
rdn_attr = uid
object_classes = posixAccount, shadowAccount

[template:pam_user:uid]
label = ユーザID
required = true
multi = false
type = text

[template:pam_user:cn]
label = 表示名
required = true
multi = false
type = text

[template:pam_user:userPassword]
label = パスワード
required = true
multi = false
type = password

[template:pam_user:uidNumber]
label = UID番号
required = true
multi = false
type = number

[template:pam_user:gidNumber]
label = GID番号
required = true
multi = false
type = number

[template:pam_user:homeDirectory]
label = ホームディレクトリ
required = true
multi = false
type = text

[template:pam_user:loginShell]
label = ログインシェル
required = true
multi = false
type = text
```

### 属性の `type` 定義

| type | 説明 |
|------|------|
| `text` | 通常のテキスト入力 |
| `password` | マスク表示。保存時はSSHAでハッシュ化してLDAPに書き込む |
| `number` | 数値入力 |
| `email` | メールアドレス入力。`@` を含む形式を必須とする |

### 環境変数

| 変数名 | 用途 | 必須 |
|--------|------|------|
| `ACCMAN_ADMIN_PASSWORD` | 管理者BINDパスワード | 必須 |
| `ACCMAN_SECRET_KEY` | セッション署名鍵 | 必須 |
| `ACCMAN_SESSION_DIR` | セッション保存ディレクトリ | 本番環境では必須 |
| `ACCMAN_CONFIG` | 設定ファイルパス（省略時: `config/accman.ini`） | 任意 |

### UI ナビゲーション構造

ログイン後のメニューから以下の画面に遷移できる。テンプレートの `scope` がメニューの振り分けに対応する。

| scope | メニュー項目 | 説明 |
|-------|-------------|------|
| `pam` | PAM設定 | ユーザ・グループ・sudoerの管理画面 |
| `mail` | メール管理 | メールアカウントの管理画面 |

---

## セッションタイムアウト

- 最終操作からタイムアウト時間を超えていた場合はセッションを強制破棄し、ログイン画面へリダイレクトする
- タイムアウト時間は管理者と一般ユーザで別々に設定ファイル（`[session]` セクション）で指定できる
- ログイン画面・ログアウト・静的ファイルへのアクセスはタイムアウトチェックの対象外とする
- ログイン画面に既ログイン状態でアクセスした場合はそのままログイン画面を表示する（タイムアウトによる強制ログアウト・リダイレクトは行わない）

---

## ログアウト

- 全画面のヘッダー右端にハンバーガーメニュー（☰）を設置し、「ログアウト」項目から明示的にログアウトできる
- ログアウト操作は POST `/logout` を呼び出してセッションを破棄する

---

## ログ出力

- ログイン成功・失敗はINFO/WARNINGレベルでログに記録する（UID・接続元IPを含む）
- LDAP操作エラーはWARNINGレベルで記録する
- journaldへの出力はデフォルトで有効（systemd管理のため）
- syslogへの追加出力は設定ファイル（`[log]` セクション）で有効化できる。facility も設定可能

---

## ヘルプ機能

- 全画面（ログイン画面を含む）にヘルプボタンを設置する
- ヘルプボタンを押すと、画面右側からヘルプドロワーがスライドして表示される
- ドロワーが開いている間は、その分だけ操作画面の表示幅を狭め、ドロワーが操作画面にかぶさらないようにする
- ドロワーは明示的な閉じる操作（✕ボタン）でのみ閉じる。ドロワー外のクリックでは閉じない
- ヘルプ内容は画面ごとに用意する
- ヘルプ内容はログインユーザの種別（管理者／一般ユーザ）に応じた説明を表示する
