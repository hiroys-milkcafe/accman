from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from ldap3.core.exceptions import LDAPException

from ..auth import get_ldap_client, login_required
from ..config import AppConfig

bp = Blueprint('pam', __name__)


@bp.route('/')
@login_required
def index():
    cfg: AppConfig = current_app.config['ACCMAN']
    templates = cfg.templates_by_scope('pam')
    if not templates:
        return render_template('pam/index.html', templates=[], current_tab=None,
                               entries=[], display_attrs=[])

    tab_id = request.args.get('tab', templates[0].id)
    current_tab = cfg.get_template(tab_id)
    if not current_tab or current_tab.scope != 'pam':
        current_tab = templates[0]

    display_attrs = [a for a in current_tab.attributes if a.type != 'password']
    attr_names = [a.attr for a in display_attrs]

    entries = []
    try:
        entries = get_ldap_client().search(cfg.pam_base_dn, '(objectClass=*)', attr_names)
    except Exception as e:
        flash(str(e), 'error')

    return render_template('pam/index.html', templates=templates,
                           current_tab=current_tab, entries=entries,
                           display_attrs=display_attrs)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    cfg: AppConfig = current_app.config['ACCMAN']

    if request.method == 'GET':
        template_id = request.args.get('template')
        template = cfg.get_template(template_id)
        if not template or template.scope != 'pam':
            return redirect(url_for('pam.index'))
        return render_template('pam/new.html', template=template)

    template_id = request.form.get('template_id', '')
    template = cfg.get_template(template_id)
    if not template or template.scope != 'pam':
        return redirect(url_for('pam.index'))

    attrs, password_attrs, errors = _collect_form_attrs(template)
    for err in errors:
        flash(err, 'error')
    if errors:
        return render_template('pam/new.html', template=template)

    rdn_val = attrs.get(template.rdn_attr)
    if isinstance(rdn_val, list):
        rdn_val = rdn_val[0] if rdn_val else ''
    if not rdn_val:
        flash(f'{template.rdn_attr} は必須です', 'error')
        return render_template('pam/new.html', template=template)

    dn = f'{template.rdn_attr}={rdn_val},{cfg.pam_base_dn}'
    try:
        get_ldap_client().add(dn, template.object_classes, attrs,
                              password_attrs=password_attrs)
        return redirect(url_for('pam.index', tab=template_id))
    except (LDAPException, Exception) as e:
        flash(str(e), 'error')
        return render_template('pam/new.html', template=template)


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    cfg: AppConfig = current_app.config['ACCMAN']

    if request.method == 'GET':
        dn = request.args.get('dn', '')
        template_id = request.args.get('template', '')
        template = cfg.get_template(template_id)
        if not dn or not template or template.scope != 'pam':
            return redirect(url_for('pam.index'))

        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names)
        if entry is None:
            flash('エントリが見つかりません', 'error')
            return redirect(url_for('pam.index'))

        return render_template('pam/edit.html', template=template, entry=entry, dn=dn)

    dn = request.form.get('dn', '')
    template_id = request.form.get('template_id', '')
    template = cfg.get_template(template_id)
    if not template or template.scope != 'pam' or not dn:
        return redirect(url_for('pam.index'))

    changes, password_attrs, errors = _collect_form_attrs(template, is_edit=True)
    for err in errors:
        flash(err, 'error')
    if errors:
        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names) or {'dn': dn}
        return render_template('pam/edit.html', template=template, entry=entry, dn=dn)

    try:
        get_ldap_client().modify(dn, changes, password_attrs=password_attrs)
        return redirect(url_for('pam.index', tab=template_id))
    except (LDAPException, Exception) as e:
        flash(str(e), 'error')
        attr_names = [a.attr for a in template.attributes if a.type != 'password']
        entry = get_ldap_client().get(dn, attr_names) or {'dn': dn}
        return render_template('pam/edit.html', template=template, entry=entry, dn=dn)


@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    dn = request.form.get('dn', '')
    tab = request.form.get('tab', '')
    if not dn:
        return redirect(url_for('pam.index'))
    try:
        get_ldap_client().delete(dn)
    except (LDAPException, Exception) as e:
        flash(str(e), 'error')
    return redirect(url_for('pam.index', tab=tab))


def _collect_form_attrs(template, is_edit: bool = False) -> tuple[dict, list[str], list[str]]:
    attrs: dict = {}
    password_attrs: list[str] = []
    errors: list[str] = []
    for attr_def in template.attributes:
        if attr_def.type == 'password':
            password_attrs.append(attr_def.attr)
            val = request.form.get(attr_def.attr, '')
            if val:
                attrs[attr_def.attr] = val
        elif attr_def.multi:
            vals = [v for v in request.form.getlist(attr_def.attr) if v]
            if vals:
                attrs[attr_def.attr] = vals
            elif attr_def.required:
                errors.append(f'{attr_def.label} は必須です')
            elif is_edit:
                attrs[attr_def.attr] = []
        else:
            val = request.form.get(attr_def.attr, '')
            if val:
                attrs[attr_def.attr] = val
            elif attr_def.required:
                errors.append(f'{attr_def.label} は必須です')
            elif is_edit:
                attrs[attr_def.attr] = []
    return attrs, password_attrs, errors
