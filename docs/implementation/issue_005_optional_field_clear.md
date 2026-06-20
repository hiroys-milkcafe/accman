# issue_005: オプション属性の空欄送信

## 決定（クローズ）

- 空欄送信 → 属性削除（MODIFY_REPLACE に空リスト）
- required: true の属性が空欄 → バリデーションエラー、保存しない
- loginShell は required: true に変更（config/accman.ini_sample）
