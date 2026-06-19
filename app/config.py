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
    bind_dn: str
    password: str


@dataclass
class AttributeDef:
    attr: str
    label: str
    required: bool
    multi: bool
    type: str  # text | password | number


@dataclass
class Template:
    id: str
    name: str
    scope: str  # pam | mail
    rdn_attr: str
    object_classes: list[str]
    attributes: list[AttributeDef]


@dataclass
class AppConfig:
    ldap: LdapConfig
    admin: AdminConfig
    pam_base_dn: str
    mail_base_dn: str
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
        bind_dn=parser['admin']['bind_dn'],
        password=admin_password,
    )

    pam_base_dn = parser['pam']['base_dn']
    mail_base_dn = parser['mail']['base_dn']

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
                ))

        templates.append(Template(
            id=tid,
            name=meta['name'],
            scope=meta['scope'],
            rdn_attr=meta['rdn_attr'],
            object_classes=object_classes,
            attributes=attributes,
        ))

    secret_key = os.environ.get('ACCMAN_SECRET_KEY')
    if not secret_key:
        raise RuntimeError('環境変数 ACCMAN_SECRET_KEY が設定されていません')

    return AppConfig(
        ldap=ldap,
        admin=admin,
        pam_base_dn=pam_base_dn,
        mail_base_dn=mail_base_dn,
        templates=templates,
    )
