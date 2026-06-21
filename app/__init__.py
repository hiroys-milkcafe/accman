import logging
import logging.handlers
import os
import time
from flask import Flask, flash, redirect, request, session, url_for
from flask_session import Session
from flask_wtf.csrf import CSRFProtect, CSRFError
from .config import load_config
from .ldap_client import CredentialExpiredError

logger = logging.getLogger('accman')


def _setup_syslog(cfg) -> None:
    if not cfg.log.syslog_enabled:
        return
    facility = logging.handlers.SysLogHandler.facility_names.get(
        cfg.log.syslog_facility.lower(),
        logging.handlers.SysLogHandler.LOG_LOCAL3,
    )
    handler = logging.handlers.SysLogHandler(address='/dev/log', facility=facility)
    handler.ident = 'accman: '
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config['SECRET_KEY'] = os.environ['ACCMAN_SECRET_KEY']
    app.config['SESSION_TYPE'] = 'filesystem'
    session_dir = os.environ.get(
        'ACCMAN_SESSION_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'sessions'),
    )
    app.config['SESSION_FILE_DIR'] = session_dir

    cfg = load_config()
    app.config['ACCMAN'] = cfg
    _setup_syslog(cfg)

    Session(app)
    CSRFProtect(app)

    _LOGIN_ENDPOINTS = {'auth.login', 'auth.admin_login', 'auth.logout', 'static'}

    @app.before_request
    def check_session_timeout():
        from flask import request
        if request.endpoint in _LOGIN_ENDPOINTS:
            return
        if 'bind_dn' not in session:
            return
        is_admin = session.get('is_admin', False)
        timeout = cfg.session.admin_timeout if is_admin else cfg.session.user_timeout
        last = session.get('last_activity')
        if last is not None and time.time() - last > timeout:
            bind_dn = session.get('bind_dn', '-')
            session.clear()
            logger.info('session timeout: %s', bind_dn)
            flash('セッションがタイムアウトしました。再度ログインしてください。', 'error')
            return redirect(url_for('auth.admin_login') if is_admin else url_for('auth.login'))
        session['last_activity'] = time.time()

    @app.context_processor
    def inject_nav():
        if 'bind_dn' in session:
            return {
                'pam_templates': cfg.templates_by_scope('pam'),
                'mail_templates': cfg.templates_by_scope('mail'),
                'is_admin': session.get('is_admin', False),
            }
        return {'pam_templates': [], 'mail_templates': [], 'is_admin': False}

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('不正なリクエストです。ページを再読み込みしてから操作してください。', 'error')
        return redirect(request.referrer or url_for('auth.index')), 400

    @app.errorhandler(CredentialExpiredError)
    def handle_credential_expired(e):
        is_admin = session.get('is_admin', False)
        bind_dn = session.get('bind_dn', '-')
        session.clear()
        logger.warning('credential expired, session cleared: %s', bind_dn)
        flash('認証情報が無効になりました。再度ログインしてください。', 'error')
        return redirect(url_for('auth.admin_login') if is_admin else url_for('auth.login'))

    from .routes.auth import bp as auth_bp
    from .routes.pam import bp as pam_bp
    from .routes.mail import bp as mail_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pam_bp, url_prefix='/pam')
    app.register_blueprint(mail_bp, url_prefix='/mail')

    return app
