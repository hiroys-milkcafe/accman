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

## 対応方針（案）

`ldap3` の `escape_dn_chars()` を使ってDNに埋め込む前にエスケープする。

```python
from ldap3.utils.dn import escape_dn_chars

bind_dn = f'uid={escape_dn_chars(uid)},{cfg.pam_base_dn}'
domain_escaped = escape_dn_chars(domain)
pamuid_escaped = escape_dn_chars(pamuid)
parent_dn = f'{container_attr}={domain_escaped},{container_attr}={pamuid_escaped},{template.base_dn}'
```

## ステータス

Open
