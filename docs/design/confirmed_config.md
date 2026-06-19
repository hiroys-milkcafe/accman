# 設定ローダー設計 (draft)

## 確定

### 設定ファイル形式

- 形式: ini
- 配置場所: `config/accman.ini`（環境変数 `ACCMAN_CONFIG` で上書き可能）
- パスワード類は設定ファイルに直書きせず環境変数で渡す

### 設定ファイル例

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

### 環境変数

| 変数名 | 用途 |
|--------|------|
| `ACCMAN_ADMIN_PASSWORD` | 管理者BINDパスワード |
| `ACCMAN_SECRET_KEY` | セッション署名鍵 |
| `ACCMAN_CONFIG` | 設定ファイルパス |

### データ構造

```python
@dataclass
class LdapConfig:
    host: str
    port: int
    tls: bool
    ca_cert: str | None

@dataclass
class AdminConfig:
    bind_dn: str
    password: str          # 環境変数 ACCMAN_ADMIN_PASSWORD から取得

@dataclass
class AttributeDef:
    attr: str
    label: str
    required: bool
    multi: bool
    type: str              # text | password | number

@dataclass
class Template:
    id: str
    name: str
    scope: str             # pam | mail
    rdn_attr: str
    object_classes: list[str]
    attributes: list[AttributeDef]

@dataclass
class AppConfig:
    ldap: LdapConfig
    admin: AdminConfig
    pam_base_dn: str
    mail_base_dn: str
    templates: list[Template]
```

### インターフェース

```python
def load_config(path: str | None = None) -> AppConfig: ...
```

### 起動時の挙動

- 必須キー欠落・環境変数未設定の場合は起動時に例外を送出してアプリを停止する
- 設定変更はアプリ再起動で反映する（ホットリロードなし）
