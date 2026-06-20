# issue_011: 一般ユーザログインが失敗する

## 状況

一般ユーザ（`/login`）でログインを試みると失敗する。エラーの詳細は未確認。

## 調査事項

以下の順で原因を切り分ける。

1. **エラーログの確認**（最初にここを見る）  
   `journalctl -u accman -f` でログイン失敗時のログを確認する。  
   ログ出力が実装されたため、`login failed: uid=...,... from ...: <LDAPエラー内容>` が出力される。

2. **BIND DN の組み立て確認**  
   `app/routes/auth.py` でBIND DNを `uid={uid},{pam_base_dn}` の形式で組み立てている。  
   `pam.base_dn` の値（`config/accman.ini` の `[pam]` セクション）が正しいか確認する。

3. **LDAPサーバへの疎通確認**  
   アプリからLDAPサーバへ接続できているか（ポート・TLS設定の確認）

4. **LDAPサーバ側のACL確認**  
   一般ユーザのSELF BINDがLDAPサーバのACLで許可されているか確認する。

## 影響範囲

- `app/routes/auth.py`（ログイン処理・エラーハンドリング）
- `config/accman.ini`（`[ldap]`・`[pam]` セクション）
