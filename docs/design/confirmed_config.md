# 設定ローダー設計 (確定)

## 設定ファイル形式

- 形式: ini
- 配置場所: `config/accman.ini`（環境変数 `ACCMAN_CONFIG` で上書き可能）
- パスワード類は設定ファイルに直書きせず環境変数で渡す

## 設定ファイル構造

```ini
[ldap]
host = ldap.example.com
port = 636
tls = true
ca_cert = /etc/ssl/certs/ca.pem

[admin]
id = admin
bind_dn = cn=admin,dc=example,dc=com

[pam]
base_dn = ou=people,dc=example,dc=com
pam_user = ou=people,dc=example,dc=com
pam_group = ou=groups,dc=example,dc=com
sudoer = ou=sudoers,dc=example,dc=com

[mail]
mail_user = ou=mail,dc=example,dc=com

[session]
admin_timeout = 3600
user_timeout = 28800

[log]
syslog_enabled = false
syslog_facility = local3

[template:pam_user]
name = PAMユーザ
scope = pam
rdn_attr = uid
object_classes = posixAccount, shadowAccount
; container_attr = ou   ← 省略時デフォルト ou

[template:pam_user:uid]
label = ユーザID
required = true
multi = false
type = text
; display_only = false  ← 省略時デフォルト false（一般ユーザも編集可）

...
```

## `[pam]` セクションの設計意図

`[pam]` セクションには **2種類の異なる用途** のキーが存在する。

### `base_dn`（ログイン専用）

一般ユーザのログイン時に BIND DN を組み立てるために使用する:

```
uid={入力uid},{base_dn}
```

テンプレートによる検索・作成とは独立して存在する。LDAPのエントリ種別（ユーザ・グループ・sudoer）がそれぞれ異なるコンテナに格納されていても、ログインに使うアカウントの格納先は1箇所に決まるため、専用のキーとして分離している。

### テンプレートIDをキーとしたエントリ格納先

```ini
pam_user = ou=people,dc=example,dc=com
pam_group = ou=groups,dc=example,dc=com
sudoer = ou=sudoers,dc=example,dc=com
```

テンプレートIDをキーとして、そのテンプレートが扱うエントリの格納先を指定する。`[template:xxx]` セクションではフォーム構造（属性・ラベル・型）を定義し、エントリの格納場所（LDAPツリー上の位置）はスコープセクション（`[pam]`/`[mail]`）で管理する設計とした。これによりLDAP環境によってエントリ種別ごとのDNが異なっていても、テンプレートセクションを変更せずに対応できる。

`[mail]` セクションには `base_dn` キーを設けない。理由: メールアカウントへの直接ログインはこのアプリが扱わないため、BIND DN 組み立てに使うグローバルな格納先を持つ必要がない。メール操作（一覧・新規作成）はすべてテンプレートIDキー（例: `mail_user`）から取得した `base_dn` で処理する。

**廃止経緯**: 旧設計では `[mail] base_dn` を mail.py の検索・新規作成に使用していたが、テンプレートごとの base_dn 管理に移行したことで用途がなくなったため廃止した。`[pam] base_dn` はログイン用途が残るため存続している。

## 環境変数

| 変数名 | 用途 | 必須 |
|--------|------|------|
| `ACCMAN_ADMIN_PASSWORD` | 管理者BINDパスワード | 必須 |
| `ACCMAN_SECRET_KEY` | セッション署名鍵 | 必須 |
| `ACCMAN_SESSION_DIR` | セッション保存ディレクトリ | 本番環境では必須 |
| `ACCMAN_CONFIG` | 設定ファイルパス（省略時: `config/accman.ini`） | 任意 |

## データ構造

```python
@dataclass
class LdapConfig:
    host: str
    port: int
    tls: bool
    ca_cert: str | None

@dataclass
class AdminConfig:
    id: str
    bind_dn: str
    password: str          # 環境変数 ACCMAN_ADMIN_PASSWORD から取得

@dataclass
class SessionConfig:
    admin_timeout: int     # 秒
    user_timeout: int      # 秒

@dataclass
class LogConfig:
    syslog_enabled: bool
    syslog_facility: str

@dataclass
class AttributeDef:
    attr: str
    label: str
    required: bool
    multi: bool
    type: str              # text | password | number
    display_only: bool     # True のとき一般ユーザ編集画面では表示のみ（デフォルト False）

@dataclass
class Template:
    id: str
    name: str
    scope: str             # pam | mail
    base_dn: str           # [pam] または [mail] セクションのテンプレートIDキーから取得
    rdn_attr: str
    object_classes: list[str]
    attributes: list[AttributeDef]
    container_attr: str    # コンテナエントリを識別するRDN属性名（デフォルト 'ou'）

@dataclass
class AppConfig:
    ldap: LdapConfig
    admin: AdminConfig
    session: SessionConfig
    log: LogConfig
    pam_base_dn: str       # [pam] base_dn。一般ユーザログインのBIND DN組み立て専用
    templates: list[Template]
```

## インターフェース

```python
def load_config(path: str | None = None) -> AppConfig: ...
```

## 起動時の挙動

- 必須キー欠落・環境変数未設定・テンプレートの base_dn 未設定の場合は起動時に例外を送出してアプリを停止する
- 設定変更はアプリ再起動で反映する（ホットリロードなし）
