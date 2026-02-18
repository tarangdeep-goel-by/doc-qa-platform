"""SQLite-based user store for authentication."""

import sqlite3
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

import bcrypt


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    role: str  # "admin" | "client"
    created_at: str
    is_active: bool = True


class UserStore:
    """SQLite-backed user CRUD."""

    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'client',
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()

    def create_user(self, email: str, password: str, role: str = "client") -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            role=role,
            created_at=datetime.now().isoformat(),
            is_active=True,
        )
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (user.id, user.email, user.password_hash, user.role, user.created_at, int(user.is_active)),
        )
        conn.commit()
        conn.close()
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_user(row)

    def get_by_id(self, user_id: str) -> Optional[User]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_user(row)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def list_users(self) -> List[User]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        conn.close()
        return [self._row_to_user(r) for r in rows]

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
        )
