import pytest
from datetime import datetime, timedelta, timezone

# Importar modelo User
from database.models.users import User, UserRole


class DummyPermission:
    def __init__(self, name, resource_type=None, action=None, scope=None):
        self.id = id(self)
        self.name = name
        self.resource_type = resource_type
        self.action = action
        self.scope = scope
        self._revoked = False
        self.is_active = True

    def is_revoked(self):
        return self._revoked


class DummyUserPermission:
    def __init__(self, permission: DummyPermission):
        self.permission = permission
        self.is_active = True
        self._revoked = False

    def is_revoked(self):
        return self._revoked


class DummyRole:
    def __init__(self, permissions):
        self._permissions = permissions

    def get_effective_permissions(self):
        return self._permissions


class DummyUserRole:
    def __init__(self, role: DummyRole):
        self.role = role
        self.is_active = True


@pytest.fixture
def user():
    return User(
        username="TestUser",
        username_norm="testuser",
        email="test@example.com",
        email_norm="test@example.com",
        role=UserRole.VIEWER,
        password_hash="hash"
    )


def test_username_normalization(user):
    assert user.username == "TestUser"
    assert user.username_norm == "testuser"


def test_email_normalization(user):
    assert user.email_norm == user.email.lower()


def test_lock_account_and_is_locked(user):
    assert not user.is_locked()
    user.lock_account(duration_minutes=1)
    assert user.is_locked()
    assert user.failed_login_attempts == 0


def test_unlock_account(user):
    user.lock_account(duration_minutes=1)
    user.unlock_account()
    assert not user.is_locked()
    assert user.failed_login_attempts == 0


def test_record_failed_login_triggers_lock(user, monkeypatch):
    # Forzar 5 intentos
    for i in range(5):
        user.record_failed_login()
    assert user.failed_login_attempts == 0  # se resetea al hacer lock_account
    assert user.is_locked()


def test_record_successful_login_resets_state(user):
    user.lock_account(duration_minutes=1)
    user.status = "locked"
    user.record_successful_login()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert user.status == "active"
    assert isinstance(user.last_login, datetime)


def test_get_effective_permissions_aggregation(user):
    # Direct permission
    p_view = DummyPermission("view_reports", resource_type=None, action=None)
    up = DummyUserPermission(p_view)
    user.user_permissions = [up]  # type: ignore

    # Role with extra permission
    p_exec = DummyPermission("execute_tests")
    role = DummyRole([p_exec])
    ur = DummyUserRole(role)
    user.user_roles = [ur]  # type: ignore

    perms = user.get_effective_permissions()
    names = {p.name for p in perms}
    assert {"view_reports", "execute_tests"} <= names


def test_has_permission_filters(user):
    p = DummyPermission("delete_users", resource_type=type("RT", (), {"value": "user"})(), action=type("ACT", (), {"value": "delete"})())
    user.user_permissions = [DummyUserPermission(p)]  # type: ignore
    assert user.has_permission("delete_users", resource_type="user", action="delete")
    assert not user.has_permission("delete_users", resource_type="system")


def test_status_check_constraint_enforced():
    # Usar una conexión real a memoria para simular constraint (creamos tabla mínima)
    import sqlite3 as sqlite
    conn = sqlite.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, username_norm TEXT UNIQUE, email TEXT, email_norm TEXT UNIQUE, password_hash TEXT, role TEXT, status TEXT CHECK (status IN ('active','inactive','locked','suspended')) )")
    # Inserción válida
    conn.execute("INSERT INTO users (username, username_norm, email, email_norm, password_hash, role, status) VALUES ('u','u','u@x','u@x','h','viewer','active')")
    # Inserción inválida
    with pytest.raises(Exception):
        conn.execute("INSERT INTO users (username, username_norm, email, email_norm, password_hash, role, status) VALUES ('b','b','b@x','b@x','h','viewer','weird')")
    conn.close()
