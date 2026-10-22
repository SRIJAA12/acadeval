"""Shared fixtures for API-level tests. These run against the real
(dev) Postgres database — there's no separate test DB in this project —
but every test runs inside an outer transaction that's rolled back
afterwards, via SQLAlchemy's savepoint-based "join an external transaction"
pattern, so nothing a test does is ever actually persisted.
"""
import uuid

import pytest
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import engine, get_db
from app.main import app
from app.models.user import User, UserRole
from app.utils.auth import hash_password, create_access_token


@pytest.fixture()
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def make_user(db_session, role: UserRole, name: str | None = None) -> User:
    uid = uuid.uuid4()
    user = User(
        id=uid,
        name=name or f"Test {role.value} {str(uid)[:8]}",
        email=f"{role.value}-{uid}@test.local",
        password_hash=hash_password("testpass123"),
        role=role,
        department="CSE",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}
