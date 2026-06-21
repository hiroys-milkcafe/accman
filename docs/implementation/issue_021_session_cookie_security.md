# issue_021: セッションCookieのSameSite・Secure未設定

## 優先度

P2

## 概要

Flask のセッションCookieに `SameSite` および `Secure` 属性が設定されていない。

- `SESSION_COOKIE_SAMESITE` 未設定（デフォルト None）: クロスサイトリクエストでもCookieが送信され、issue_020（CSRF）の攻撃難易度を下げる
- `SESSION_COOKIE_SECURE` 未設定（デフォルト False）: HTTPSが有効になった際にもCookieが平文通信で送信されてしまう

## 対象ファイル

- `app/__init__.py`（`SESSION_COOKIE_SAMESITE`・`SESSION_COOKIE_SECURE` の追加）

## 対応方針（案）

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS設定（issue_022）完了後に有効化
```

`SameSite=Lax` にすることで、通常のリンク遷移（GETリクエスト）ではCookieが送信されるが、クロスサイトPOSTではCookieが送信されなくなる。これによりissue_020（CSRF）の攻撃難易度を大幅に上げる補完的対策となる。

`Secure` フラグはHTTPS化（issue_022）が完了してから有効化する。

## ステータス

Open
