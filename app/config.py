import configparser
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LdapConfig:
    host: str
    port: int
    tls: bool
    ca_cert: Optional[str]


@dataclass
class AdminConfig:
    id: str
    bind_dn: str
    password: str


@dataclass
class SessionConfig:
    admin_timeout: int   # seconds
    user_timeout: int    # seconds
    secure_cookie: bool  # True: Cookie に Secure フラグを付与（NGINX が HTTPS を終端する環境で使用）


@dataclass
class LogConfig:
    syslog_enabled: bool
    syslog_facility: str  # e.g. 'local3'


@dataclass
class AttributeDef:
    attr: str
    label: str
    required: bool
    multi: bool
    type: str  # text | password | number
    display_only: bool = False  # True のとき一般ユーザには表示のみ（管理者は通常通り編集可）


@dataclass
class Template:
    id: str
    name: str
    scope: str  # pam | mail
    base_dn: str
    rdn_attr: str
    object_classes: list[str]
    attributes: list[AttributeDef]
    container_attr: str = 'ou'  # コンテナエントリ（OU等）を識別するRDN属性名


@dataclass
class AppConfig:
    ldap: LdapConfig
    admin: AdminConfig
    session: SessionConfig
    log: LogConfig
    pam_base_dn: str  # 一般ユーザログインのBIND DN組み立て用
    templates: list[Template]

    def templates_by_scope(self, scope: str) -> list[Template]:
        return [t for t in self.templates if t.scope == scope]

    def get_template(self, template_id: str) -> Optional[Template]:
        return next((t for t in self.templates if t.id == template_id), None)


def load_config(path: Optional[str] = None) -> AppConfig:
    config_path = path or os.environ.get('ACCMAN_CONFIG', 'config/accman.ini')

    parser = configparser.ConfigParser()
    if not parser.read(config_path):
        raise RuntimeError(f'設定ファイルが見つかりません: {config_path}')

    ldap_sec = parser['ldap']
    ldap = LdapConfig(
        host=ldap_sec['host'],
        port=int(ldap_sec.get('port', '389')),
        tls=ldap_sec.getboolean('tls', False),
        ca_cert=ldap_sec.get('ca_cert') or None,
    )

    admin_password = os.environ.get('ACCMAN_ADMIN_PASSWORD')
    if not admin_password:
        raise RuntimeError('環境変数 ACCMAN_ADMIN_PASSWORD が設定されていません')

    admin = AdminConfig(
        id=parser['admin']['id'],
        bind_dn=parser['admin']['bind_dn'],
        password=admin_password,
    )

    session_sec = parser['session']
    session_cfg = SessionConfig(
        admin_timeout=int(session_sec['admin_timeout']),
        user_timeout=int(session_sec['user_timeout']),
        secure_cookie=session_sec.getboolean('secure_cookie', False),
    )

    log_cfg = LogConfig(
        syslog_enabled=parser.getboolean('log', 'syslog_enabled', fallback=False),
        syslog_facility=parser.get('log', 'syslog_facility', fallback='local3'),
    )

    pam_base_dn = parser['pam']['base_dn']

    # テンプレートIDを出現順に収集
    template_ids: list[str] = []
    for section in parser.sections():
        parts = section.split(':')
        if len(parts) == 2 and parts[0] == 'template':
            tid = parts[1]
            if tid not in template_ids:
                template_ids.append(tid)

    templates: list[Template] = []
    for tid in template_ids:
        meta = parser[f'template:{tid}']
        object_classes = [c.strip() for c in meta['object_classes'].split(',')]

        attributes: list[AttributeDef] = []
        for section in parser.sections():
            parts = section.split(':')
            if len(parts) == 3 and parts[0] == 'template' and parts[1] == tid:
                attr_name = parts[2]
                a = parser[section]
                attributes.append(AttributeDef(
                    attr=attr_name,
                    label=a['label'],
                    required=a.getboolean('required', False),
                    multi=a.getboolean('multi', False),
                    type=a.get('type', 'text'),
                    display_only=a.getboolean('display_only', False),
                ))

        scope = meta['scope']
        scope_section = parser[scope] if scope in parser else {}
        template_base_dn = scope_section.get(tid)
        if not template_base_dn:
            raise RuntimeError(
                f'テンプレート "{tid}" の base_dn が [{scope}] セクションに設定されていません'
            )

        templates.append(Template(
            id=tid,
            name=meta['name'],
            scope=scope,
            base_dn=template_base_dn,
            rdn_attr=meta['rdn_attr'],
            object_classes=object_classes,
            attributes=attributes,
            container_attr=meta.get('container_attr', 'ou'),
        ))

    secret_key = os.environ.get('ACCMAN_SECRET_KEY')
    if not secret_key:
        raise RuntimeError('環境変数 ACCMAN_SECRET_KEY が設定されていません')

    return AppConfig(
        ldap=ldap,
        admin=admin,
        session=session_cfg,
        log=log_cfg,
        pam_base_dn=pam_base_dn,
        templates=templates,
    )
