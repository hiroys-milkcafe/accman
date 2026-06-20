from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from ldap3.core.exceptions import LDAPException

from ..config import AppConfig
from ..ldap_client import LdapClient

bp = Blueprint('auth', __name__)


@bp.route('/')
def index():
    if 'bind_dn' not in session:
        return redirect(url_for('auth.login'))
    return render_template('index.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid = request.form.get('uid', '').strip()
        password = request.form.get('password', '')
        cfg: AppConfig = current_app.config['ACCMAN']
        bind_dn = f'uid={uid},{cfg.pam_base_dn}'
        try:
            LdapClient(cfg.ldap, bind_dn, password).bind_test()
            session.clear()
            session['bind_dn'] = bind_dn
            session['password'] = password
            session['is_admin'] = False
            return redirect(url_for('auth.index'))
        except (LDAPException, Exception):
            flash('ログインに失敗しました', 'error')
    return render_template('login.html')


@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        uid = request.form.get('uid', '').strip()
        password = request.form.get('password', '')
        cfg: AppConfig = current_app.config['ACCMAN']
        if uid != cfg.admin.id:
            flash('ログインに失敗しました', 'error')
            return render_template('admin/login.html')
        try:
            LdapClient(cfg.ldap, cfg.admin.bind_dn, password).bind_test()
            session.clear()
            session['bind_dn'] = cfg.admin.bind_dn
            session['password'] = password
            session['is_admin'] = True
            return redirect(url_for('auth.index'))
        except (LDAPException, Exception):
            flash('ログインに失敗しました', 'error')
    return render_template('admin/login.html')


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
