"""Tests for UserStore SQLite CRUD."""

import sqlite3
import pytest

from src.user_store import UserStore, User


class TestUserStoreInit:
    """Test initialization."""

    def test_creates_db_and_table(self, tmp_path):
        db_path = str(tmp_path / "users.db")
        store = UserStore(db_path=db_path)
        # Table should exist
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        conn.close()


class TestCreateUser:
    """Test create_user()."""

    def test_basic(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        user = store.create_user("test@example.com", "password123")
        assert user.email == "test@example.com"
        assert user.role == "client"
        assert user.is_active is True
        assert user.id  # UUID assigned
        assert user.password_hash != "password123"  # Hashed

    def test_duplicate_email_raises(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        store.create_user("test@example.com", "pass1")
        with pytest.raises(sqlite3.IntegrityError):
            store.create_user("test@example.com", "pass2")

    def test_admin_role(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        user = store.create_user("admin@example.com", "pass", role="admin")
        assert user.role == "admin"

    def test_email_normalized(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        user = store.create_user("  Test@Example.COM  ", "pass")
        assert user.email == "test@example.com"


class TestGetByEmail:
    """Test get_by_email()."""

    def test_found(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        created = store.create_user("test@example.com", "pass")
        found = store.get_by_email("test@example.com")
        assert found is not None
        assert found.id == created.id

    def test_not_found(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        assert store.get_by_email("missing@example.com") is None

    def test_case_insensitive(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        store.create_user("test@example.com", "pass")
        found = store.get_by_email("TEST@EXAMPLE.COM")
        assert found is not None


class TestGetById:
    """Test get_by_id()."""

    def test_found(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        created = store.create_user("test@example.com", "pass")
        found = store.get_by_id(created.id)
        assert found is not None
        assert found.email == "test@example.com"

    def test_not_found(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        assert store.get_by_id("nonexistent-id") is None


class TestVerifyPassword:
    """Test verify_password()."""

    def test_correct(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        user = store.create_user("test@example.com", "mypassword")
        assert store.verify_password("mypassword", user.password_hash) is True

    def test_wrong(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        user = store.create_user("test@example.com", "mypassword")
        assert store.verify_password("wrongpassword", user.password_hash) is False


class TestListUsers:
    """Test list_users()."""

    def test_ordered(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        store.create_user("a@example.com", "pass")
        store.create_user("b@example.com", "pass")
        users = store.list_users()
        assert len(users) == 2
        # Ordered by created_at DESC (most recent first)
        assert users[0].email == "b@example.com"

    def test_empty(self, tmp_path):
        store = UserStore(db_path=str(tmp_path / "users.db"))
        assert store.list_users() == []
