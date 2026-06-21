# issue_022: nginxのHTTPS未設定（平文通信）

## 優先度

P3

## 概要

nginx の設定がHTTP（port 80）のみであり、セッションCookieおよびLDAP BINDパスワードを含む全通信が平文でネットワーク上を流れる。社内ネットワーク限定の運用とはいえ、内部からの盗聴によってセッションIDを取得される可能性がある。

## 対象ファイル

- `nginx/accman.conf`（TLS設定の追加）
- `app/__init__.py`（`SESSION_COOKIE_SECURE = True` の有効化。issue_021 と連動）

## 対応方針（案）

1. 証明書（自己署名またはプライベートCA）を用意
2. nginx に `listen 443 ssl` ・証明書パスを設定
3. HTTP → HTTPS リダイレクト設定
4. `SESSION_COOKIE_SECURE = True` を有効化（issue_021 と同時対応）

## 備考

インフラ側の変更が伴うため、P1・P2 の対応完了後に着手する。

## ステータス

Open
