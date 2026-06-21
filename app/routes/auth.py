import logging

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from ldap3.core.exceptions import LDAPException
from ldap3.utils.dn import escape_rdn

from ..config import AppConfig
from ..ldap_client import LdapClient

logger = logging.getLogger('accman')

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
        bind_dn = f'uid={escape_rdn(uid) if uid else ""},{cfg.pam_base_dn}'
        client_ip = request.headers.get('X-Real-IP', request.remote_addr)
        try:
            LdapClient(cfg.ldap, bind_dn, password).bind_test()
            session.clear()
            session['bind_dn'] = bind_dn
            session['password'] = password
            session['is_admin'] = False
            logger.info('login success: %s from %s', bind_dn, client_ip)
            return redirect(url_for('auth.index'))
        except (LDAPException, Exception) as e:
            logger.warning('login failed: %s from %s: %s', bind_dn, client_ip, e)
            flash('ログインに失敗しました', 'error')
    return render_template('login.html')


@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        uid = request.form.get('uid', '').strip()
        password = request.form.get('password', '')
        cfg: AppConfig = current_app.config['ACCMAN']
        client_ip = request.headers.get('X-Real-IP', request.remote_addr)
        if uid != cfg.admin.id:
            logger.warning('admin login failed: invalid admin id from %s', client_ip)
            flash('ログインに失敗しました', 'error')
            return render_template('admin/login.html')
        try:
            LdapClient(cfg.ldap, cfg.admin.bind_dn, password).bind_test()
            session.clear()
            session['bind_dn'] = cfg.admin.bind_dn
            session['password'] = password
            session['is_admin'] = True
            logger.info('admin login success: %s from %s', cfg.admin.bind_dn, client_ip)
            return redirect(url_for('auth.index'))
        except (LDAPException, Exception) as e:
            logger.warning('admin login failed: %s from %s: %s', cfg.admin.bind_dn, client_ip, e)
            flash('ログインに失敗しました', 'error')
    return render_template('admin/login.html')


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
