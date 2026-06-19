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

```sh
# 任意のパスに配置する（以下は /opt/accman を使用する例）
cp -r accman/ /opt/accman
cd /opt/accman

python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config/accman.ini` を環境に合わせて編集する。

```ini
[ldap]
host = ldap.example.com   # LDAPサーバのホスト名またはIPアドレス
port = 636                 # TLS使用時は 636、平文は 389
tls = true                 # true / false
; ca_cert = /etc/ssl/certs/ca.pem  # 自己署名証明書の場合はコメントを外す

[admin]
bind_dn = cn=admin,dc=example,dc=com  # 管理者のBIND DN

[pam]
base_dn = ou=people,dc=example,dc=com  # PAMアカウントのベースDN

[mail]
base_dn = ou=mail,dc=example,dc=com    # メールアカウントのベースDN
```

テンプレートセクション（`[template:*]`）は環境のLDAPスキーマに合わせて追加・変更する。
サンプルとして `pam_user` / `pam_group` / `sudoer` / `mail_user` が同梱されている。

#### テンプレート属性の `type` 値

| type | 説明 |
|------|------|
| `text` | テキスト入力 |
| `password` | マスク表示。保存時はSSHAでハッシュ化してLDAPに書き込む |
| `number` | 数値入力 |

### 4. 環境変数の設定

パスワードとセッション鍵は設定ファイルに書かず、環境変数で渡す。

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
chown www-data:www-data /var/lib/accman/sessions
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

### 6. systemd サービスの設定

`/etc/systemd/system/accman.service` を作成する:

```ini
[Unit]
Description=accman LDAP account manager
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/accman
EnvironmentFile=/etc/accman/env
ExecStart=/opt/accman/venv/bin/python run.py
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
| 管理者 | `/admin/login` | パスワードのみ | 設定ファイルの `admin.bind_dn` ＋ 入力パスワードでBIND |
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
   /opt/accman/venv/bin/pip install -r /opt/accman/requirements.txt
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
| `/opt/accman/config/accman.ini` | アプリ設定ファイル（LDAP接続先・テンプレート定義） |
| `/etc/accman/env` | 環境変数ファイル（パスワード・秘密鍵） |
| `/var/lib/accman/sessions/` | セッションファイル保存ディレクトリ（`ACCMAN_SESSION_DIR` で指定） |
| `/opt/accman/venv/` | Python仮想環境（再インストールで再作成） |
| `/etc/nginx/conf.d/accman.conf` | NGINXの設定ファイル |
| `/etc/systemd/system/accman.service` | systemdサービスユニット |
