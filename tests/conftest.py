import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.fixture(scope="session")
def test_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL/PostGIS test database")
    # Migrations use app.db.engine; the URL must be set before imports/engine initialization.
    assert (make_url(url).database or "").endswith("_test"), "Use a dedicated *_test database"
    os.environ["DATABASE_URL"] = url
    from app import db

    original = db.engine
    db.engine = create_engine(url, pool_pre_ping=True)
    command.upgrade(Config("alembic.ini"), "head")
    command.downgrade(Config("alembic.ini"), "base")
    command.upgrade(Config("alembic.ini"), "head")
    yield db.engine
    db.engine.dispose()
    db.engine = original


@pytest.fixture
def session(test_engine) -> Iterator[Session]:
    connection = test_engine.connect()
    transaction = connection.begin()
    with Session(connection, expire_on_commit=False) as session:
        yield session
    transaction.rollback()
    connection.close()
