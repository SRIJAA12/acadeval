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


DEMO_USERS = [
    {
        "name": "Priya Sharma",
        "email": "priya@college.edu",
        "role": UserRole.student,
        "department": "Computer Science & Engineering",
        "roll_no": "CS2021001",
    },
    {
        "name": "Dr. Meera Krishnan",
        "email": "meera@college.edu",
        "role": UserRole.guide,
        "department": "Computer Science & Engineering",
    },
    {
        "name": "Prof. Suresh Rajan",
        "email": "suresh@college.edu",
        "role": UserRole.reviewer,
        "department": "Computer Science & Engineering",
    },
    {
        "name": "Dr. K. V. Ramanathan",
        "email": "hod@college.edu",
        "role": UserRole.hod,
        "department": "Computer Science & Engineering",
    },
]


def seed_demo_users() -> None:
    db = SessionLocal()
    try:
        pass_hash = hash_password("demo123")
        created = 0
        for udata in DEMO_USERS:
            existing = db.query(User).filter(User.email == udata["email"]).first()
            if not existing:
                db.add(User(
                    email=udata["email"],
                    name=udata["name"],
                    role=udata["role"],
                    department=udata.get("department", "CSE"),
                    roll_no=udata.get("roll_no"),
                    password_hash=pass_hash,
                    is_active=True,
                ))
                created += 1
        db.commit()
        if created:
            print(f"Seeded {created} demo users (password: demo123).")
        else:
            print("Demo users already exist.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_bootstrap_admin()
    seed_demo_users()
