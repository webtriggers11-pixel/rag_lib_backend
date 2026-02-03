#!/usr/bin/env python3
"""Seed one admin user. Run from project root: python scripts/seed_admin.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.auth.auth_service import count_users, create_user

SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123")


def seed_admin():
    if count_users() > 0:
        print("Users already exist. Skipping seed.")
        return
    user = create_user(SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD, role="admin", org_id=None)
    print(f"Admin created: {user['email']} (id={user['id']})")


if __name__ == "__main__":
    seed_admin()
