import logging

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from ldap3.core.exceptions import LDAPException

from ..auth import get_ldap_client, login_required
from ..config import AppConfig
from ..ldap_client import CredentialExpiredError
from .common import collect_form_attrs

logger = logging.getLogger('accman')

bp = Blueprint('mail', __name__)


def _entry_sort_key(dn: str, base_dn: str) -> tuple:
    """DN を base_dn からの相対パス（親→子順）のタプルで返す。ソート・深さ計算に使用。"""
    base_parts = [p.strip().lower() for p in base_dn.split(',')]
    dn_parts = [p.strip().lower() for p in dn.split(',')]
    relative = dn_parts[:len(dn_parts) - len(base_parts)]
    return tuple(reversed(relative))


@bp.route('/')
@login_required
def index():
    cfg: AppConfig = current_app.config['ACCMAN']
    templates = cfg.templates_by_scope('mail')
    if not templates:
        return render_template('mail/index.html', templates=[], current_tab=None,
                               entries=[], display_attrs=[])

    tab_id = request.args.get('tab', templates[0].id)
    current_tab = cfg.get_template(tab_id)
    if not current_tab or current_tab.scope != 'mail':
        current_tab = templates[0]

    display_attrs = [a for a in current_tab.attributes if a.type != 'password']
    attr_names = [a.attr for a in display_attrs]

    entries = []
    try:
        raw = get_ldap_client().search(current_tab.base_dn, '(objectClass=*)', attr_names)
        # base_dn エントリ自体を除外（SUBTREE 検索で含まれる場合がある）
        entries = [e for e in raw
                   if e['dn'].lower() != current_tab.base_dn.lower()]
    except CredentialExpiredError:
        raise
    except Exception as e:
        logger.warning('LDAP search failed: %s: %s', current_tab.base_dn, e)
        flash(str(e), 'error')

    # DN 階層順にソートし、depth とコンテナフラグを付与
    container_prefix = current_tab.container_attr.lower() + '='
    entries.sort(key=lambda e: _entry_sort_key(e['dn'], current_tab.base_dn))

    for entry in entries:
        key = _entry_sort_key(entry['dn'], current_tab.base_dn)
        rdn = entry['dn'].split(',')[0].lower()
        is_container = rdn.startswith(container_prefix)
        entry['_depth'] = len(key) - 1
        entry['_is_container'] = is_container
        entry['_container_label'] = entry['dn'].split(',')[0] if is_container else ''

    return render_template('mail/index.html', templates=templates,
                           current_tab=current_tab, entries=entries,
                           display_attrs=display_attrs)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    cfg: AppConfig = current_app.config['ACCMAN']

    if request.method == 'GET':
        template_id = request.args.get('template')
        template = cfg.get_template(template_id)
        if not template or template.scope != 'mail':
            return redirect(url_for('mail.index'))
        return render_template('mail/new.html', template=template)

    template_id = request.form.get('template_id', '')
    template = cfg.get_template(template_id)
    if not template or template.scope != 'mail':
        return redirect(url_for('mail.index'))

    attrs, password_attrs, errors = collect_form_attrs(template)
    for err in errors:
        flash(err, 'error')
    if errors:
        return render_template('mail/new.html', template=template)

    rdn_val = attrs.get(template.rdn_attr)
    if isinstance(rdn_val, list):
        rdn_val = rdn_val[0] if rdn_val else ''
    if not rdn_val:
        flash(f'{template.rdn_attr} は必須です', 'error')
        return render_template('mail/new.html', template=template)

    if not session.get('is_admin'):
        mail_vals = attrs.get('mail', [])
        first_mail = mail_vals[0] if mail_vals else ''
        if '@' not in first_mail:
            flash('メールアドレスの形式が正しくありません（@ が含まれていません）', 'error')
            return render_template('mail/new.html', template=template)

        domain = first_mail.split('@', 1)[1]

        bind_dn = session.get('bind_dn', '')
        rdn_part = bind_dn.split(',', 1)[0] if bind_dn else ''
        pamuid = rdn_part.split('=', 1)[1] if '=' in rdn_part else ''
        if not pamuid:
            flash('セッション情報の取得に失敗しました', 'error')
            return redirect(url_for('auth.index'))

        container_attr = template.container_attr
        parent_dn = f'{container_attr}={domain},{container_attr}={pamuid},{template.base_dn}'

        if get_ldap_client().get(parent_dn, ['objectClass']) is None:
            flash(f'ドメイン "{domain}" が存在しません。管理者にドメインの作成を依頼してください。', 'error')
            return render_template('mail/new.html', template=template)

        dn = f'{template.rdn_attr}={rdn_val},{parent_dn}'
    else:
        dn = f'{template.rdn_attr}={rdn_val},{template.base_dn}'

    try:
        get_ldap_client().add(dn, template.object_classes, attrs,
                              password_attrs=password_attrs)
        return redirect(url_for('mail.index', tab=template_id))
    except CredentialExpiredError:
        raise
    except (LDAPException, Exception) as e:
        logger.warning('LDAP add failed: %s: %s', dn, e)
        flash(str(e), 'error')
        return render_template('mail/new.html', template=template)


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    cfg: AppConfig = current_app.config['ACCMAN']

    if request.method == 'GET':
        dn = request.args.get('dn', '')
        template_id = request.args.get('template', '')
        template = cfg.get_template(template_id)
        if not dn or not template or template.scope != 'mail':
            return redirect(url_for('mail.index'))

        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names)
        if entry is None:
            flash('エントリが見つかりません', 'error')
            return redirect(url_for('mail.index'))

        return render_template('mail/edit.html', template=template, entry=entry, dn=dn)

    dn = request.form.get('dn', '')
    template_id = request.form.get('template_id', '')
    template = cfg.get_template(template_id)
    if not template or template.scope != 'mail' or not dn:
        return redirect(url_for('mail.index'))

    skip_attrs = set() if session.get('is_admin') else {
        a.attr for a in template.attributes if a.display_only
    }
    changes, password_attrs, errors = collect_form_attrs(template, is_edit=True,
                                                         skip_attrs=skip_attrs)
    for err in errors:
        flash(err, 'error')
    if errors:
        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names) or {'dn': dn}
        return render_template('mail/edit.html', template=template, entry=entry, dn=dn)

    changes.pop(template.rdn_attr, None)
    try:
        get_ldap_client().modify(dn, changes, password_attrs=password_attrs)
        return redirect(url_for('mail.index', tab=template_id))
    except CredentialExpiredError:
        raise
    except (LDAPException, Exception) as e:
        logger.warning('LDAP modify failed: %s: %s', dn, e)
        flash(str(e), 'error')
        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names) or {'dn': dn}
        return render_template('mail/edit.html', template=template, entry=entry, dn=dn)


@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    dn = request.form.get('dn', '')
    tab = request.form.get('tab', '')
    if not dn:
        return redirect(url_for('mail.index'))
    try:
        get_ldap_client().delete(dn)
    except CredentialExpiredError:
        raise
    except (LDAPException, Exception) as e:
        logger.warning('LDAP delete failed: %s: %s', dn, e)
        flash(str(e), 'error')
    return redirect(url_for('mail.index', tab=tab))
