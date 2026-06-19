# アーキテクチャ設計 (確定)

## コンポーネント構成

```
[ブラウザ]
    │ HTTP
    ▼
[NGINX]  ← リバースプロキシ / 静的ファイル配信
    │ HTTP (localhost)
    ▼
[Python Webアプリ]
    ├── 設定ローダー
    ├── LDAPクライアント層
    ├── 認証・セッション層
    └── ルーティング層
            ├── /login, /admin/login, /logout
            ├── /pam/**
            └── /mail/**
    │
    ▼
[LDAPサーバ]
```

## 技術スタック

| 用途 | 採用 |
|------|------|
| Webフレームワーク | Flask |
| テンプレートエンジン | Jinja2（Flask組み込み） |
| LDAPライブラリ | ldap3 |
| セッション管理 | Flask-Session（サーバサイド） |
| フロントエンドプロキシ | NGINX |

## ディレクトリ構成

```
accman/
├── config/
│   └── accman.ini
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── ldap_client.py
│   ├── auth.py
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── pam.py
│       └── mail.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── admin/
│   │   └── login.html
│   ├── pam/
│   │   ├── index.html
│   │   ├── new.html
│   │   └── edit.html
│   └── mail/
│       ├── index.html
│       ├── new.html
│       └── edit.html
├── static/
│   ├── css/
│   └── js/
├── nginx/
│   └── accman.conf
├── requirements.txt
└── run.py
```
