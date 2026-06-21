# issue_023: LDAPのDN構築時にユーザ入力が未エスケープ

## 優先度

P4

## 概要

以下2箇所でユーザ入力をエスケープなしにLDAPのDN文字列へ直接埋め込んでいる。DNの特殊文字（`,` `=` `+` `<` `>` `;` `\` `"`）が含まれた場合、意図しないDNが構築される可能性がある。

```python
# app/routes/auth.py:28
bind_dn = f'uid={uid},{cfg.pam_base_dn}'   # uid はフォーム入力そのまま

# app/routes/mail.py:127
parent_dn = f'{container_attr}={domain},{container_attr}={pamuid},{template.base_dn}'
# domain はメールアドレスの @ 以降をそのまま使用
```

## 影響範囲と緩和要因

- 検索フィルタはすべてハードコード（`'(objectClass=*)'`）のためフィルタインジェクションは発生しない
- 不正なDNによるLDAP BINDは失敗するだけで権限昇格には繋がらない
- LDAP ACLが最終的な権限制御を担っているため、実害は限定的
- 上記から現時点での攻撃可能性は低い

## 実装内容

issue_023 に記載の2箇所に加え、コードレビューで同パターンの注入点をさらに3箇所確認。合計5箇所に `ldap3.utils.dn.escape_dn_chars()` を適用した。

| ファイル | 対象変数 |
|---|---|
| `app/routes/auth.py:29` | `uid`（ログインフォーム入力） |
| `app/routes/pam.py:101` | `rdn_val`（新規エントリフォーム入力） |
| `app/routes/mail.py:128` | `domain`（メールアドレスの@以降）、`pamuid`（セッションのbind_dnから抽出） |
| `app/routes/mail.py:134` | `rdn_val`（一般ユーザの新規エントリフォーム入力） |
| `app/routes/mail.py:136` | `rdn_val`（管理者の新規エントリフォーム入力） |

## 検証結果

- 通常の英数字uid・rdn_val は escape_rdn で変換されず既存データへの影響なし
- DN特殊文字を含むuid（例: `dang,ou=injected`）→「ログインに失敗しました」で正常エラー処理
- 空uid → 修正前は500、修正後は「ログインに失敗しました」で正常エラー処理（`escape_rdn('')` の IndexError に対するガードを追加）
- 管理者・一般ユーザともに正常ログイン・PAM・メール画面の動作確認済み

## ステータス

Closed
