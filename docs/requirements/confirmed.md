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

1. 管理者のBIND DNはバックエンド設定ファイルに記載する
2. `/admin/login` でuid＋パスワードを入力する
3. 設定ファイルのRootDN＋入力パスワードでLDAPにBINDする
4. BIND成功後、管理者セッションとして保持する

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
  - PAM用BaseDN
  - メール用BaseDN（PAMと同一ルートから分岐するケースを想定）

---

## スキーマ・エントリテンプレート

- 特定のObjectClassをコードにハードコードしない
- 「PAMユーザ」「PAMグループ」「メールユーザ」等のエントリ種別ごとに、使用するObjectClassと属性の一覧を設定ファイルで定義する（テンプレート方式）
- UIはテンプレートに基づいてフォームを構成する

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
ca_cert = /etc/ssl/certs/ca.pem

[admin]
bind_dn = cn=admin,dc=example,dc=com

[pam]
base_dn = ou=people,dc=example,dc=com

[mail]
base_dn = ou=mail,dc=example,dc=com

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
required = false
multi = false
type = text
```

### 属性の `type` 定義

| type | 説明 |
|------|------|
| `text` | 通常のテキスト入力 |
| `password` | マスク表示。保存時はSSHAでハッシュ化してLDAPに書き込む |
| `number` | 数値入力 |

### 環境変数

| 変数名 | 用途 |
|--------|------|
| `ACCMAN_ADMIN_PASSWORD` | 管理者BINDパスワード |
| `ACCMAN_SECRET_KEY` | セッション署名鍵 |
| `ACCMAN_CONFIG` | 設定ファイルパス（省略時: `config/accman.ini`） |

### UI ナビゲーション構造

ログイン後のメニューから以下の画面に遷移できる。テンプレートの `scope` がメニューの振り分けに対応する。

| scope | メニュー項目 | 説明 |
|-------|-------------|------|
| `pam` | PAM設定 | ユーザ・グループ・sudoerの管理画面 |
| `mail` | メール管理 | メールアカウントの管理画面 |
