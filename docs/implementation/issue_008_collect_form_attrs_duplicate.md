# issue_008: _collect_form_attrs の重複

## 状況

`app/routes/pam.py` と `app/routes/mail.py` にまったく同じ内容の `_collect_form_attrs` 関数が存在する。どちらかを修正した際にもう一方の更新を忘れると挙動が乖離するリスクがある。

## 修正方針

共通関数として `app/routes/common.py`（または `app/form_utils.py`）などに切り出し、両ファイルからインポートする。

## 決定（クローズ）

`app/routes/common.py` に `collect_form_attrs` として切り出し、`pam.py` / `mail.py` 双方からインポートするよう修正済み。
