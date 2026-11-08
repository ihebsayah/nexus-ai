"""Alembic environment: offline SQL or explicitly guarded disposable database."""

import os

import sqlalchemy as sa
from alembic import context
from alembic.util.exc import CommandError
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from nexus.persistence.migration_settings import (
    TEST_DATABASE_MARKER,
    MigrationSafetyError,
    MigrationSettings,
    settings_from_environment,
)
from nexus.persistence.models import Base

config = context.config


def run_offline() -> None:
    context.configure(
        dialect_name="postgresql",
        target_metadata=Base.metadata,
        literal_binds=True,
        transactional_ddl=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.execute("SET LOCAL search_path TO public")
        context.run_migrations()


def run_online() -> None:
    supplied = config.attributes.get("nexus_migration_settings")
    settings = (
        supplied
        if isinstance(supplied, MigrationSettings)
        else settings_from_environment(os.environ)
    )
    url = URL.create(
        "postgresql+psycopg",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )
    engine = sa.create_engine(
        url,
        poolclass=NullPool,
        hide_parameters=True,
        echo=False,
        connect_args={"connect_timeout": 3},
    )
    try:
        with engine.connect() as connection, connection.begin():
            if config.attributes.get("nexus_read_only", False):
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql("SET LOCAL search_path TO public")
            actual = connection.execute(
                sa.text(
                    "SELECT current_database(), shobj_description(oid, 'pg_database') "
                    "FROM pg_database WHERE datname = current_database()"
                )
            ).one()
            if actual[0] != settings.database or actual[1] != TEST_DATABASE_MARKER:
                raise MigrationSafetyError(
                    "Disposable database identity/ownership marker does not match."
                )
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                compare_type=True,
                compare_server_default=True,
                include_schemas=False,
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


try:
    if context.is_offline_mode():
        run_offline()
    else:
        run_online()
except (MigrationSafetyError, sa.exc.SQLAlchemyError, OSError):
    raise CommandError(
        "Migration target/connection failed; sensitive details suppressed."
    ) from None
