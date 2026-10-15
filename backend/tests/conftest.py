import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.services.llm.mock import MockRecipeExtractor
from app.services.transcript.mock import MockTranscriptProvider

# ── Test database URL ─────────────────────────────────────────────────────────
# Must point to a real PostgreSQL instance (not SQLite) because the schema uses
# PostgreSQL-specific JSONB columns.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://recipelens:recipelens@localhost:5432/recipelens_test",
)

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    """
    Run Alembic migrations against the test database before the test session.
    This verifies the migration files themselves are correct — not just the ORM
    models — catching drift between models and migrations early.
    """
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}")
    yield
    # Teardown: drop all tables so the next run starts clean
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic downgrade base failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture()
def db():
    """
    Yield a DB session isolated by a savepoint-aware nested transaction.

    Pattern:
      1. Open a connection and begin an outer transaction.
      2. Start a SAVEPOINT (nested transaction) for each test.
      3. Patch Session.commit() to issue RELEASE SAVEPOINT + new SAVEPOINT
         instead of a real COMMIT, keeping all writes within the outer
         transaction.
      4. Roll back the outer transaction at teardown — all test writes vanish.

    This works correctly with SQLAlchemy 2.x and PostgreSQL.
    """
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Begin a nested transaction (SAVEPOINT)
    nested = connection.begin_nested()

    # Each time the session commits, restart the savepoint so subsequent
    # writes in the same test are still within the outer transaction.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """
    TestClient with:
    1. get_db → the savepoint-isolated test session (for request handlers).
    2. SessionLocal in jobs.py → returns the same test session (for background tasks).
    3. app.state providers → mock implementations (no external calls).

    No module-level monkey-patching. All overrides go through FastAPI's
    dependency_overrides or app.state, which are the correct extension points.
    """
    import app.api.v1.routes.jobs as jobs_module

    original_session_local = jobs_module.SessionLocal

    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Replace SessionLocal in the jobs module so the background task wrapper
    # also uses the test session. This is the minimal surface needed — the
    # factory is only called in one place (_run_pipeline_with_own_session).
    jobs_module.SessionLocal = lambda: db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        # Override providers AFTER lifespan runs so the lifespan's own
        # get_providers() call (which may construct a real Gemini/OpenAI client
        # depending on the active .env) is replaced with cheap mocks.
        app.state.transcript_provider = MockTranscriptProvider()
        app.state.recipe_extractor = MockRecipeExtractor()
        yield c

    app.dependency_overrides.clear()
    jobs_module.SessionLocal = original_session_local
    # Reset app.state providers (will be re-set by lifespan on next real startup)
    del app.state.transcript_provider
    del app.state.recipe_extractor
