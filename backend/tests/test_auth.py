"""Tests for JWT auth dependencies and helpers."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from fastapi import HTTPException

from src.user_store import User


def _run(coro):
    """Run an async function synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestCreateAccessToken:
    """Test create_access_token()."""

    @patch("api.auth.JWT_SECRET", "a" * 32)
    @patch("api.auth.JWT_ACCESS_EXPIRY_MINUTES", 15)
    def test_structure(self):
        from api.auth import create_access_token
        from jose import jwt

        token = create_access_token("user1", "admin")
        payload = jwt.decode(token, "a" * 32, algorithms=["HS256"])
        assert payload["sub"] == "user1"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "exp" in payload

    @patch("api.auth.JWT_SECRET", "a" * 32)
    @patch("api.auth.JWT_ACCESS_EXPIRY_MINUTES", 15)
    def test_expiry(self):
        from api.auth import create_access_token
        from jose import jwt

        token = create_access_token("user1", "admin")
        payload = jwt.decode(token, "a" * 32, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = (exp - now).total_seconds()
        assert 14 * 60 < diff < 16 * 60


class TestCreateRefreshToken:
    """Test create_refresh_token()."""

    @patch("api.auth.JWT_SECRET", "a" * 32)
    @patch("api.auth.JWT_REFRESH_EXPIRY_DAYS", 7)
    def test_type(self):
        from api.auth import create_refresh_token
        from jose import jwt

        token = create_refresh_token("user1")
        payload = jwt.decode(token, "a" * 32, algorithms=["HS256"])
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user1"


class TestDecodeToken:
    """Test _decode_token()."""

    @patch("api.auth.JWT_SECRET", "a" * 32)
    def test_valid(self):
        from api.auth import _decode_token, create_access_token

        token = create_access_token("user1", "admin")
        payload = _decode_token(token, "access")
        assert payload["sub"] == "user1"

    @patch("api.auth.JWT_SECRET", "a" * 32)
    def test_invalid_token(self):
        from api.auth import _decode_token

        with pytest.raises(HTTPException) as exc_info:
            _decode_token("invalid.token.here", "access")
        assert exc_info.value.status_code == 401

    @patch("api.auth.JWT_SECRET", "a" * 32)
    def test_wrong_type(self):
        from api.auth import _decode_token, create_refresh_token

        token = create_refresh_token("user1")
        with pytest.raises(HTTPException) as exc_info:
            _decode_token(token, "access")
        assert exc_info.value.status_code == 401
        assert "token type" in str(exc_info.value.detail).lower()


class TestGetCurrentUser:
    """Test get_current_user() async dependency."""

    @patch("api.auth.AUTH_ENABLED", False)
    def test_b2c_returns_anonymous(self):
        from api.auth import get_current_user, ANONYMOUS_USER

        request = MagicMock()
        user = _run(get_current_user(request))
        assert user == ANONYMOUS_USER
        assert user.role == "admin"

    @patch("api.auth.AUTH_ENABLED", True)
    def test_no_header_raises(self):
        from api.auth import get_current_user

        request = MagicMock()
        request.headers.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(request))
        assert exc_info.value.status_code == 401

    @patch("api.auth.AUTH_ENABLED", True)
    @patch("api.auth.JWT_SECRET", "a" * 32)
    def test_invalid_bearer_raises(self):
        from api.auth import get_current_user

        request = MagicMock()
        request.headers.get.return_value = "Bearer invalid.token"
        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(request))
        assert exc_info.value.status_code == 401

    @patch("api.auth.AUTH_ENABLED", True)
    @patch("api.auth.JWT_SECRET", "a" * 32)
    @patch("api.auth.JWT_ACCESS_EXPIRY_MINUTES", 15)
    def test_valid_token_returns_user(self):
        from api.auth import get_current_user, create_access_token

        mock_user = User(
            id="u1", email="test@test.com", password_hash="h",
            role="admin", created_at="2025-01-01", is_active=True,
        )
        token = create_access_token("u1", "admin")

        request = MagicMock()
        request.headers.get.return_value = f"Bearer {token}"
        request.app.state.user_store = MagicMock()
        request.app.state.user_store.get_by_id.return_value = mock_user

        user = _run(get_current_user(request))
        assert user.id == "u1"

    @patch("api.auth.AUTH_ENABLED", True)
    @patch("api.auth.JWT_SECRET", "a" * 32)
    @patch("api.auth.JWT_ACCESS_EXPIRY_MINUTES", 15)
    def test_inactive_user_raises(self):
        from api.auth import get_current_user, create_access_token

        mock_user = User(
            id="u1", email="test@test.com", password_hash="h",
            role="admin", created_at="2025-01-01", is_active=False,
        )
        token = create_access_token("u1", "admin")

        request = MagicMock()
        request.headers.get.return_value = f"Bearer {token}"
        request.app.state.user_store = MagicMock()
        request.app.state.user_store.get_by_id.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            _run(get_current_user(request))
        assert exc_info.value.status_code == 401


class TestRequireAdmin:
    """Test require_admin() dependency."""

    def test_admin_passes(self):
        from api.auth import require_admin

        admin_user = User(
            id="u1", email="admin@test.com", password_hash="h",
            role="admin", created_at="2025-01-01",
        )
        result = _run(require_admin(admin_user))
        assert result.role == "admin"

    def test_non_admin_raises(self):
        from api.auth import require_admin

        client_user = User(
            id="u2", email="client@test.com", password_hash="h",
            role="client", created_at="2025-01-01",
        )
        with pytest.raises(HTTPException) as exc_info:
            _run(require_admin(client_user))
        assert exc_info.value.status_code == 403


class TestBuildDocumentList:
    """Test build_document_list() helper."""

    def test_with_chats(self):
        from api.helpers import build_document_list
        from src.models import DocumentMetadata, Chat

        doc = DocumentMetadata(
            doc_id="d1", title="Test", filename="t.pdf",
            file_path="/tmp/t.pdf", format="pdf",
            upload_date="2025-01-01", file_size_mb=1.0, chunk_count=5,
        )
        chat = Chat(
            id="c1", name="Chat 1", doc_ids=["d1"],
            created_at="2025-01-01", updated_at="2025-01-01",
        )

        doc_store = MagicMock()
        doc_store.list_documents.return_value = [doc]
        chat_mgr = MagicMock()
        chat_mgr.list_chats.return_value = [chat]

        result = build_document_list(doc_store, chat_mgr)
        assert len(result) == 1
        assert result[0].chat_count == 1
        assert result[0].chats[0].id == "c1"

    def test_no_chats(self):
        from api.helpers import build_document_list
        from src.models import DocumentMetadata

        doc = DocumentMetadata(
            doc_id="d1", title="Test", filename="t.pdf",
            file_path="/tmp/t.pdf", format="pdf",
            upload_date="2025-01-01", file_size_mb=1.0,
        )

        doc_store = MagicMock()
        doc_store.list_documents.return_value = [doc]
        chat_mgr = MagicMock()
        chat_mgr.list_chats.return_value = []

        result = build_document_list(doc_store, chat_mgr)
        assert result[0].chat_count == 0
        assert result[0].chats == []
