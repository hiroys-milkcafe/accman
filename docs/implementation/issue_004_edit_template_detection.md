# issue_004: 編集画面でのテンプレート判定

## 決定（クローズ）

一覧画面の編集リンクに `template=<template_id>` を含めることで、編集画面は URL パラメータからテンプレートを取得する。objectClass によるテンプレート判定は行わない。

編集リンク例: `/pam/edit?dn=uid=john,ou=people,...&template=pam_user`
