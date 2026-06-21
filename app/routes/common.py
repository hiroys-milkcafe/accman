from flask import request


def collect_form_attrs(template, is_edit: bool = False,
                       skip_attrs: set = None) -> tuple[dict, list[str], list[str]]:
    skip_attrs = skip_attrs or set()
    attrs: dict = {}
    password_attrs: list[str] = []
    errors: list[str] = []
    for attr_def in template.attributes:
        if attr_def.attr in skip_attrs:
            continue
        if attr_def.type == 'password':
            password_attrs.append(attr_def.attr)
            val = request.form.get(attr_def.attr, '')
            if val:
                attrs[attr_def.attr] = val
        elif attr_def.multi:
            vals = [v for v in request.form.getlist(attr_def.attr) if v]
            if vals:
                attrs[attr_def.attr] = vals
                if attr_def.type == 'email' and any('@' not in v for v in vals):
                    errors.append(f'{attr_def.label} の形式が正しくありません（メールアドレスを入力してください）')
            elif attr_def.required:
                errors.append(f'{attr_def.label} は必須です')
            elif is_edit:
                attrs[attr_def.attr] = []
        else:
            val = request.form.get(attr_def.attr, '')
            if val:
                attrs[attr_def.attr] = val
                if attr_def.type == 'email' and '@' not in val:
                    errors.append(f'{attr_def.label} の形式が正しくありません（メールアドレスを入力してください）')
            elif attr_def.required:
                errors.append(f'{attr_def.label} は必須です')
            elif is_edit:
                attrs[attr_def.attr] = []
    return attrs, password_attrs, errors
