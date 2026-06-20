# issue_012: mail/edit.html パスワードモーダルの確認欄・エラー表示欠落

## 状態（Closed）

`mail/edit.html` にパスワード確認欄（`modal-pw-confirm`）とエラー表示要素（`modal-pw-error`）を追加して解決。

## 原因

`multi_field.js` の `openPasswordModal()` / `confirmPassword()` は `modal-pw-confirm` と `modal-pw-error` の2要素を参照するが、`mail/edit.html` にはこれらが存在しなかった。`pam/edit.html` は commit `3e25743` で正しく追加されていたが、`mail/edit.html` への反映が漏れていた。

## 症状

- パスワード不一致時にエラーが表示されず、「設定済み」バッジが表示される（誤動作）
- パスワードが実際には hidden input にセットされないため、保存しても変更されない

## 修正内容

`templates/mail/edit.html` のパスワードモーダル内に以下を追加:

```html
<div class="field">
  <label for="modal-pw-confirm">新しいパスワード（確認）</label>
  <input type="password" id="modal-pw-confirm">
</div>
<p id="modal-pw-error" class="field-error" style="display:none">パスワードが一致しません</p>
```

## 確認済み動作

- パスワード不一致時: 赤文字エラー表示、保存されない
- パスワード一致時: 「設定済み」バッジ表示、hidden inputに値がセットされてPOSTに含まれる
