import os
from flask import Flask, session
from flask_session import Session
from .config import load_config


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

    Session(app)

    @app.context_processor
    def inject_nav():
        if 'bind_dn' in session:
            return {
                'pam_templates': cfg.templates_by_scope('pam'),
                'mail_templates': cfg.templates_by_scope('mail'),
                'is_admin': session.get('is_admin', False),
            }
        return {'pam_templates': [], 'mail_templates': [], 'is_admin': False}

    from .routes.auth import bp as auth_bp
    from .routes.pam import bp as pam_bp
    from .routes.mail import bp as mail_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pam_bp, url_prefix='/pam')
    app.register_blueprint(mail_bp, url_prefix='/mail')

    return app
