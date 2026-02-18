"""Seed an admin user. Idempotent — skips if email already exists.

Usage:
    python -m scripts.seed_admin --email admin@example.com --password secret
"""

import argparse
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.user_store import UserStore


def main():
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--db", default="data/users.db")
    args = parser.parse_args()

    store = UserStore(db_path=args.db)

    existing = store.get_by_email(args.email)
    if existing:
        print(f"User {args.email} already exists (id={existing.id}, role={existing.role}). Skipping.")
        return

    user = store.create_user(email=args.email, password=args.password, role="admin")
    print(f"Admin user created: {user.email} (id={user.id})")


if __name__ == "__main__":
    main()
