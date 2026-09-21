"""Optionally create one environment-configured bootstrap administrator."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.utils.auth import hash_password


def seed_bootstrap_admin() -> None:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    if not email:
        print("Bootstrap administrator seed skipped.")
        return

    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters."
        )
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Bootstrap Administrator").strip()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("Bootstrap administrator already exists.")
            return
        db.add(User(
            name=name,
            roll_no=None,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.hod,
            department=os.getenv("BOOTSTRAP_ADMIN_DEPARTMENT", "CSE"),
            is_active=True,
        ))
        db.commit()
        print("Bootstrap administrator created. No sample projects or scores were added.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_bootstrap_admin()
