import base64
import hashlib
import os

from ldap3 import ALL, MODIFY_REPLACE, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPException

from .config import LdapConfig


def _hash_ssha(plain: str) -> str:
    salt = os.urandom(4)
    digest = hashlib.sha1(plain.encode('utf-8') + salt).digest()
    return '{SSHA}' + base64.b64encode(digest + salt).decode('ascii')


class LdapClient:
    def __init__(self, config: LdapConfig, bind_dn: str, password: str):
        self._config = config
        self._bind_dn = bind_dn
        self._password = password

    def _connect(self) -> Connection:
        server = Server(
            self._config.host,
            port=self._config.port,
            use_ssl=self._config.tls,
            get_info=ALL,
            tls=self._build_tls() if self._config.tls else None,
        )
        conn = Connection(server, self._bind_dn, self._password, auto_bind=True)
        return conn

    def _build_tls(self):
        if not self._config.ca_cert:
            return None
        from ldap3 import Tls
        import ssl
        return Tls(ca_certs_file=self._config.ca_cert, validate=ssl.CERT_REQUIRED)

    def bind_test(self) -> None:
        conn = self._connect()
        conn.unbind()

    def search(self, base_dn: str, filter: str, attrs: list[str]) -> list[dict]:
        conn = self._connect()
        try:
            conn.search(base_dn, filter, SUBTREE, attributes=attrs)
            results = []
            for entry in conn.entries:
                row: dict = {'dn': entry.entry_dn}
                for attr in attrs:
                    try:
                        vals = entry[attr].values
                        row[attr] = [str(v) for v in vals]
                    except Exception:
                        row[attr] = []
                results.append(row)
            return results
        finally:
            conn.unbind()

    def get(self, dn: str, attrs: list[str]) -> dict | None:
        conn = self._connect()
        try:
            conn.search(dn, '(objectClass=*)', attributes=attrs)
            if not conn.entries:
                return None
            entry = conn.entries[0]
            result: dict = {'dn': entry.entry_dn}
            for attr in attrs:
                try:
                    result[attr] = [str(v) for v in entry[attr].values]
                except Exception:
                    result[attr] = []
            return result
        finally:
            conn.unbind()

    def add(self, dn: str, object_classes: list[str], attrs: dict,
            password_attrs: list[str] | None = None) -> None:
        actual: dict = {}
        for attr, val in attrs.items():
            if attr in (password_attrs or []):
                plain = val[0] if isinstance(val, list) else val
                if plain:
                    actual[attr] = _hash_ssha(str(plain))
            else:
                actual[attr] = val

        conn = self._connect()
        try:
            conn.add(dn, object_classes, actual)
            if conn.result['result'] != 0:
                raise LDAPException(conn.result.get('description', 'LDAP error'))
        finally:
            conn.unbind()

    def modify(self, dn: str, changes: dict,
               password_attrs: list[str] | None = None) -> None:
        ldap_changes: dict = {}
        for attr, val in changes.items():
            if attr in (password_attrs or []):
                plain = val[0] if isinstance(val, list) else val
                if plain:
                    ldap_changes[attr] = [(MODIFY_REPLACE, [_hash_ssha(str(plain))])]
            else:
                vals = val if isinstance(val, list) else [val]
                ldap_changes[attr] = [(MODIFY_REPLACE, [str(v) for v in vals])]

        if not ldap_changes:
            return

        conn = self._connect()
        try:
            conn.modify(dn, ldap_changes)
            if conn.result['result'] != 0:
                raise LDAPException(conn.result.get('description', 'LDAP error'))
        finally:
            conn.unbind()

    def delete(self, dn: str) -> None:
        conn = self._connect()
        try:
            conn.delete(dn)
            if conn.result['result'] != 0:
                raise LDAPException(conn.result.get('description', 'LDAP error'))
        finally:
            conn.unbind()
