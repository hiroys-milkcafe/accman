# issue_019: Safari で type=email の入力欄が他項目より小さく表示される

## 状態（Closed）

## 問題

`type = email` を設定した入力欄が Safari で他の入力欄より小さく表示された。

## 原因

`style.css` のフォーム入力スタイルセレクタに `input[type=email]` が含まれておらず、
`width: 100%` や `padding`・`border`・`font-size` がブラウザのデフォルトスタイルのまま適用されていた。

## 対応

`style.css` の `.field input` セレクタに `input[type=email]` を追加。

変更ファイル: `static/css/style.css`
