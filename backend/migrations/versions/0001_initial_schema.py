"""Initial domain and audit schema, frozen from Architecture section 10.2.

Revision ID: 0001_initial_schema
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 200", name="ck_customers_name_length"
        ),
        sa.CheckConstraint("position('@' in email) > 1", name="ck_customers_email_at"),
    )
    op.create_index(
        "customers_email_lower_uidx", "customers", [sa.text("lower(email)")], unique=True
    )
    op.create_index("customers_name_lower_idx", "customers", [sa.text("lower(name)")])
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expected_delivery_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_orders_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint(
            "expected_delivery_at >= created_at", name="ck_orders_expected_delivery"
        ),
    )
    op.create_index(
        "orders_pending_idx",
        "orders",
        [sa.text("created_at ASC"), sa.text("id ASC")],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "orders_overdue_idx",
        "orders",
        [sa.text("expected_delivery_at ASC"), sa.text("id ASC")],
        postgresql_where=sa.text("status NOT IN ('delivered', 'cancelled')"),
    )
    op.create_index(
        "orders_customer_created_idx",
        "orders",
        ["customer_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_table(
        "shipment_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_shipment_events"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_shipment_events_order_id_orders",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "event_type IN ('created', 'picked_up', 'in_transit', 'out_for_delivery', "
            "'delivered', 'exception')",
            name="ck_shipment_events_event_type",
        ),
    )
    op.create_index(
        "shipment_events_order_occurred_idx",
        "shipment_events",
        ["order_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False, server_default=sa.text("'local'")),
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("args_hash", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.CheckConstraint(
            "event_type IN ('request', 'tool_decision', 'grounding', 'error')",
            name="ck_audit_events_event_type",
        ),
        sa.CheckConstraint(
            "decision IN ('allowed', 'denied', 'completed', 'error')",
            name="ck_audit_events_decision",
        ),
        sa.CheckConstraint("row_count >= 0", name="ck_audit_events_row_count"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_audit_events_latency_ms"),
    )
    op.create_index(
        "audit_events_request_idx", "audit_events", ["request_id", sa.text("created_at ASC")]
    )
    op.create_index("audit_events_created_idx", "audit_events", [sa.text("created_at ASC")])


def downgrade() -> None:
    op.drop_index("audit_events_created_idx", table_name="audit_events")
    op.drop_index("audit_events_request_idx", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("shipment_events_order_occurred_idx", table_name="shipment_events")
    op.drop_table("shipment_events")
    op.drop_index("orders_customer_created_idx", table_name="orders")
    op.drop_index("orders_overdue_idx", table_name="orders")
    op.drop_index("orders_pending_idx", table_name="orders")
    op.drop_table("orders")
    op.drop_index("customers_name_lower_idx", table_name="customers")
    op.drop_index("customers_email_lower_uidx", table_name="customers")
    op.drop_table("customers")
