from functools import wraps

from flask import current_app, redirect, session, url_for

from .ldap_client import LdapClient


def get_ldap_client() -> LdapClient:
    cfg = current_app.config['ACCMAN']
    return LdapClient(cfg.ldap, session['bind_dn'], session['password'])


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'bind_dn' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
