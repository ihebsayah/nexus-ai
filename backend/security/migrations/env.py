"""Separate initial-only environment; original M1.3 environment is unchanged."""

from alembic import context
from alembic.util.exc import CommandError
from sqlalchemy.engine import Connection

config = context.config
connection = config.attributes.get("connection")
if (
    context.is_offline_mode()
    or not config.attributes.get("initial_only")
    or not isinstance(connection, Connection)
):
    raise CommandError("Only the guarded initial-only caller may use this environment.")
if context.get_revision_argument() != "0001_initial_schema":
    raise CommandError("Only exact initial revision application is supported.")
connection.exec_driver_sql("SET LOCAL search_path = public")
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
