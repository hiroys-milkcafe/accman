# LDAPクライアント層設計 (draft)

## 確定

### 責務

- LDAPへの接続・BIND・CRUD操作を抽象化し、上位層に統一したインターフェースを提供する
- 上位層はLDAPプロトコルの詳細を意識しない

### インターフェース

```python
class CredentialExpiredError(Exception):
    """LDAPのBINDがinvalidCredentialsで失敗したときに送出する。"""

class LdapClient:
    def __init__(self, config: LdapConfig, bind_dn: str, password: str): ...

    def bind_test(self) -> None: ...
    def search(self, base_dn: str, filter: str, attrs: list[str]) -> list[dict]: ...
    def get(self, dn: str, attrs: list[str]) -> dict | None: ...
    def add(self, dn: str, object_classes: list[str], attrs: dict,
            password_attrs: list[str] | None = None) -> None: ...
    def modify(self, dn: str, changes: dict,
               password_attrs: list[str] | None = None) -> None: ...
    def delete(self, dn: str) -> None: ...
```

### 接続方式

- 操作ごとに接続・BIND・切断を行う（コネクションプールなし）

### パスワード書き込み

- `type: password` の属性値はSSHAでハッシュ化してからLDAPに書き込む
- ハッシュ化はLDAPクライアント層が行う

### エラー処理

- BIND時に `invalidCredentials` が返った場合は `CredentialExpiredError` を送出する
- その他のBIND失敗・操作失敗（権限不足・エントリ不在等）は `LDAPException` として上位層へ伝える
- `CredentialExpiredError` はアプリ全体の `@app.errorhandler` で補足し、セッション破棄・ログイン画面リダイレクトを行う（[認証・セッション設計](confirmed_auth.md) 参照）
