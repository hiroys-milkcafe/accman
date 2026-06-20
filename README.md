# accman

LDAPを通じて PAMアカウント（ユーザ・グループ・sudoer）とMTA用メールアカウントを管理するWebベースのLDAPクライアント。

## 動作環境

- OS: AlmaLinux 9
- Python: 3.9 以上

## 概要

| 項目 | 内容 |
|------|------|
| バックエンド | Python (Flask) |
| フロントエンドプロキシ | NGINX |
| LDAPライブラリ | ldap3 |
| セッション管理 | Flask-Session（ファイルシステム） |

ブラウザ → NGINX（リバースプロキシ） → Flask（127.0.0.1:5000） → LDAPサーバ の構成で動作する。

---

## 導入手順

### 1. 前提パッケージのインストール

```sh
dnf install python3 python3-pip nginx
```

### 2. アプリケーションの配置

実行ユーザとグループを作成する:

```sh
groupadd --system accman
useradd --system --no-create-home --shell /sbin/nologin --gid accman accman
```

アプリを配置し、仮想環境を構築する:

```sh
# 任意のパスに配置する（以下は /opt/accman を使用する例）
cp -r accman/ /opt/accman

python3 -m venv /opt/venv
/opt/venv/bin/pip install -r /opt/accman/requirements.txt
```

### 3. 設定ファイルの編集

`config/accman.ini_sample` をコピーして `config/accman.ini` を作成し、環境に合わせて編集する。

```sh
cp config/accman.ini_sample config/accman.ini
```

`config/accman.ini` は git 管理外（`.gitignore` で除外済み）のため、`git pull` やアーカイブの上書き展開で既存の設定が失われることはない。`config/accman.ini_sample` が設定項目を追加した場合は差分を手動で `config/accman.ini` へ反映すること。

```ini
[ldap]
host = ldap.example.com   # LDAPサーバのホスト名またはIPアドレス
port = 636                 # TLS使用時は 636、平文は 389
tls = true                 # true / false
; ca_cert = /etc/ssl/certs/ca.pem  # 自己署名証明書の場合はコメントを外す

[admin]
bind_dn = cn=admin,dc=example,dc=com  # 管理者のBIND DN

[pam]
base_dn = ou=people,dc=example,dc=com  # 一般ユーザログインのBIND DN組み立て用
pam_user = ou=people,dc=example,dc=com # テンプレートIDをキーにしたエントリ格納先
pam_group = ou=groups,dc=example,dc=com
sudoer = ou=sudoers,dc=example,dc=com

[mail]
mail_user = ou=mail,dc=example,dc=com  # テンプレートIDをキーにしたエントリ格納先
```

#### テンプレートセクション

テンプレートは「エントリの種別（PAMユーザ・グループ・メールユーザ等）」を定義する設定ブロック。UIのタブ・フォーム項目・一覧カラムがこの定義に従って自動生成される。サンプルとして `pam_user` / `pam_group` / `sudoer` / `mail_user` が同梱されている。環境のLDAPスキーマに合わせて追加・変更する。

**セクション構造**

```
[template:<テンプレートID>]           ← テンプレートのヘッダー（1個）
[template:<テンプレートID>:<属性名>]   ← 属性定義（属性の数だけ記載）
```

テンプレートIDは英数字・アンダースコアで任意に命名する（例: `pam_user`）。ファイル内の記載順がUIの表示順になる。

**テンプレートヘッダーのキー**

| キー | 説明 | 値の例 |
|------|------|--------|
| `name` | 画面に表示するテンプレート名 | `PAMユーザ` |
| `scope` | 表示先のメニュー | `pam` または `mail` |
| `rdn_attr` | エントリDN生成に使うLDAP属性名 | `uid` |
| `object_classes` | 付与するobjectClass（カンマ区切り） | `posixAccount, shadowAccount` |

`rdn_attr` を `uid`、`pam.base_dn` を `ou=people,dc=example,dc=com` とした場合、新規エントリのDNは `uid=<入力値>,ou=people,dc=example,dc=com` になる。

**テンプレート属性のキー**

| キー | 説明 | 値 |
|------|------|----|
| `label` | フォームのラベル（日本語可） | 任意の文字列 |
| `required` | 必須入力かどうか | `true` / `false` |
| `multi` | 複数値を入力できるかどうか | `true` / `false` |
| `type` | 入力欄の種類 | `text` / `password` / `number` |

`required = false`（任意項目）を空欄で保存すると、その属性がLDAPエントリから削除される。

**`type` の値**

| type | 説明 |
|------|------|
| `text` | テキスト入力 |
| `password` | マスク表示。保存時はSSHAでハッシュ化してLDAPに書き込む |
| `number` | 数値入力 |

**テンプレート追加例（カスタムスキーマ）**

```ini
[template:my_type]
name = カスタムエントリ
scope = pam
rdn_attr = cn
object_classes = myObjectClass

[template:my_type:cn]
label = エントリ名
required = true
multi = false
type = text

[template:my_type:description]
label = 説明
required = false
multi = false
type = text
```

### 4. 環境変数の設定

パスワードとセッション鍵は設定ファイルに書かず、環境変数で渡す。
本番環境では後述の Step 6 で作成する `/etc/accman/env` に記載し、systemd の `EnvironmentFile=` を通じてアプリに渡す。

| 変数名 | 用途 | 必須 |
|--------|------|------|
| `ACCMAN_ADMIN_PASSWORD` | 管理者（RootDN）のBINDパスワード | 必須 |
| `ACCMAN_SECRET_KEY` | Flaskセッション署名鍵（推測困難なランダム文字列） | 必須 |
| `ACCMAN_SESSION_DIR` | セッション保存ディレクトリ | 本番環境では必須 |
| `ACCMAN_CONFIG` | 設定ファイルパス（省略時: `config/accman.ini`） | 任意 |

`ACCMAN_SECRET_KEY` の生成例:

```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`ACCMAN_SESSION_DIR` はアプリ起動ユーザのホームディレクトリ下などを指定する（例: `/var/lib/accman/sessions`）。
未設定時のデフォルト `var/sessions/`（アプリルート相対）は開発用であり、本番環境では使用しないこと。

```sh
# セッション保存ディレクトリを作成する例
mkdir -p /var/lib/accman/sessions
chown accman:accman /var/lib/accman/sessions
chmod 700 /var/lib/accman/sessions
```

### 5. NGINX の設定

```sh
cp /opt/accman/nginx/accman.conf /etc/nginx/conf.d/accman.conf
nginx -t
systemctl reload nginx
```

`nginx/accman.conf` のデフォルト設定は HTTP（ポート80）、静的ファイルは `/opt/accman/static/` を直接配信する。
別のパスに配置した場合や HTTPS を使う場合は `accman.conf` を適宜編集する。

バックエンド停止時（502 等）はアプリの `static/50x.html` を返す設定が含まれている。カスタムエラーページを別パスに置く場合は `accman.conf` の以下の箇所を編集する:

```nginx
error_page 500 502 503 504 /50x.html;
location = /50x.html {
    root /opt/accman/static;
    internal;
}
```

### 6. systemd サービスの設定

`/etc/systemd/system/accman.service` を作成する:

```ini
[Unit]
Description=accman LDAP account manager
After=network.target

[Service]
Type=simple
User=accman
WorkingDirectory=/opt/accman
EnvironmentFile=/etc/accman/env
ExecStart=/opt/venv/bin/python run.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

環境変数ファイル `/etc/accman/env` を作成し、パーミッションを制限する:

```sh
mkdir -p /etc/accman
cat > /etc/accman/env <<'EOF'
ACCMAN_ADMIN_PASSWORD=（管理者パスワード）
ACCMAN_SECRET_KEY=（生成したランダム文字列）
ACCMAN_SESSION_DIR=/var/lib/accman/sessions
EOF
chmod 600 /etc/accman/env
chown root:root /etc/accman/env
```

### 7. サービスの起動

```sh
systemctl daemon-reload
systemctl enable --now accman
systemctl status accman
```

正常起動したらブラウザで `http://（サーバのIPまたはFQDN）/` にアクセスして動作を確認する。

---

## 管理者向け情報

### ログイン種別

| 種別 | ログインURL | 入力項目 | BIND方法 |
|------|-------------|---------|---------|
| 管理者 | `/admin/login` | ID ＋ パスワード | 入力IDを `admin.id` と照合後、設定ファイルの `admin.bind_dn` ＋ 入力パスワードでBIND |
| 一般ユーザ | `/login` | uid ＋ パスワード | `uid={uid},{pam_base_dn}` を組み立ててBIND |

管理者の bind_dn は設定ファイルに記載するため、管理者ログイン画面での uid 入力は不要。
一般ユーザのアクセス制御はLDAPサーバのACLに委ねる（アプリ側で独自ACLは持たない）。

### セッションファイルのセキュリティ

セッションファイルには LDAP の bind_dn とパスワードが保存される。
`ACCMAN_SESSION_DIR` に指定したディレクトリをアプリ実行ユーザのみ読み書きできるよう権限を制限すること（導入手順4参照）。

### 設定変更の反映

設定ファイル（`accman.ini`）を変更した場合、アプリを再起動することで反映される。ホットリロードはない。

```sh
systemctl restart accman
```

### セッションの削除

ユーザのセッションを強制的に無効化したい場合は `ACCMAN_SESSION_DIR` に設定したディレクトリのファイルを削除する。
アプリは再起動不要で、次のリクエスト時に再ログインが要求される。

```sh
rm -f /var/lib/accman/sessions/*
```

### ログ確認

```sh
journalctl -u accman -f
```

### アップデート手順

1. サービスを停止する:
   ```sh
   systemctl stop accman
   ```
2. ソースを更新する（git pull または再配置）。
3. 依存パッケージを更新する:
   ```sh
   /opt/venv/bin/pip install -r /opt/accman/requirements.txt
   ```
4. サービスを起動する:
   ```sh
   systemctl start accman
   ```

設定ファイル（`config/accman.ini`）と環境変数ファイル（`/etc/accman/env`）はアップデートで上書きされないことを確認してから手順を進める。

### 再インストール手順

環境を作り直す場合、設定と環境変数ファイルを先に退避しておく。

```sh
cp -p /etc/accman/env /tmp/accman_env.bak
cp -p /opt/accman/config/accman.ini /tmp/accman.ini.bak
```

アプリを再配置したあと、退避したファイルを元の場所に戻してサービスを起動する。
セッションディレクトリ（`ACCMAN_SESSION_DIR` に設定したパス）はアプリ外に置いているため、再インストールの影響を受けない。

### ファイルとディレクトリの役割

| パス | 説明 |
|------|------|
| `/opt/accman/config/accman.ini_sample` | 設定ファイルのサンプル（git管理。直接は使用しない） |
| `/opt/accman/config/accman.ini` | アプリ設定ファイル（`accman.ini_sample` をコピーして作成。git管理外） |
| `/etc/accman/env` | 環境変数ファイル（パスワード・秘密鍵） |
| `/var/lib/accman/sessions/` | セッションファイル保存ディレクトリ（`ACCMAN_SESSION_DIR` で指定） |
| `/opt/venv/` | Python仮想環境（再インストールで再作成） |
| `/etc/nginx/conf.d/accman.conf` | NGINXの設定ファイル |
| `/etc/systemd/system/accman.service` | systemdサービスユニット |
