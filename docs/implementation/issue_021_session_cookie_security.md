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

## 実装内容

- `SESSION_COOKIE_SAMESITE = 'Lax'` を固定設定（HTTP/HTTPS共通）
- `SESSION_COOKIE_SECURE` を `cfg.session.secure_cookie`（`config/accman.ini` の `[session] secure_cookie`）で制御
  - HTTPS環境: `secure_cookie = true` でSecureフラグ付与
  - HTTP環境: `secure_cookie = false`（デフォルト）でSecureフラグなし

## 検証結果

- HTTPS環境（secure_cookie=true）: `SameSite=Lax; Secure` が付与されることを確認
- HTTP環境（secure_cookie=false）: `SameSite=Lax` のみ付与、Secureフラグなしを確認
- 一般ユーザ・管理者ともに正常ログイン・操作を確認
- CSRF保護・セッション認証チェックのリグレッションなし

## ステータス

Closed
