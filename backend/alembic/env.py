import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make sure the app package is importable from alembic/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.models.job  # noqa: E402, F401 — register models with metadata
import app.models.recipe  # noqa: E402, F401
from app.db.base import Base  # noqa: E402

config = context.config

# Override sqlalchemy.url from the DATABASE_URL environment variable.
# Raise a clear error early rather than letting SQLAlchemy produce a cryptic
# "no connection string" message when the variable is missing.
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Export it before running alembic, e.g.:\n"
        "  export DATABASE_URL=postgresql://user:pass@host:5432/dbname"
    )
config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
