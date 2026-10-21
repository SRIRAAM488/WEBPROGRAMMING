"""Pytest configuration.

The DATABASE_URL environment variable is set *before* any app module is
imported, so every test runs against a throwaway SQLite file instead of your
real ``dailyflow.db``.
"""

import os
import tempfile
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / "dailyflow_pytest.db"

# Remove any leftover file from a previous run.
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
# Never seed demo data during automated tests.
os.environ["SEED_ON_STARTUP"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.settings_service import get_app_settings, get_hydration_settings  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Drop and recreate every table before each test.

    autouse=True means each test starts from a known-empty database, so tests
    can never interfere with each other or with your demo data.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Re-create the two single-row settings tables.
    session = SessionLocal()
    try:
        get_app_settings(session)
        get_hydration_settings(session)
    finally:
        session.close()

    yield


@pytest.fixture
def client():
    """A FastAPI TestClient wired to the test database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    """A direct SQLAlchemy session, for tests that need to inspect the database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()