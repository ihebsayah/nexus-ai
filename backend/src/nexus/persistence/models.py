"""Initial PostgreSQL mappings from Architecture section 10.2."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared metadata; importing it neither connects nor creates objects."""


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 200", name="ck_customers_name_length"
        ),
        sa.CheckConstraint("position('@' in email) > 1", name="ck_customers_email_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    email: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


sa.Index("customers_email_lower_uidx", sa.func.lower(Customer.email), unique=True)
sa.Index("customers_name_lower_idx", sa.func.lower(Customer.name))


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
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

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")
    )
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    expected_delivery_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )


sa.Index(
    "orders_pending_idx",
    Order.created_at.asc(),
    Order.id.asc(),
    postgresql_where=sa.text("status = 'pending'"),
)
sa.Index(
    "orders_overdue_idx",
    Order.expected_delivery_at.asc(),
    Order.id.asc(),
    postgresql_where=sa.text("status NOT IN ('delivered', 'cancelled')"),
)
sa.Index("orders_customer_created_idx", Order.customer_id, Order.created_at.desc(), Order.id.desc())


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"
    __table_args__ = (
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

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")
    )
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)


sa.Index(
    "shipment_events_order_occurred_idx",
    ShipmentEvent.order_id,
    ShipmentEvent.occurred_at.desc(),
    ShipmentEvent.id.desc(),
)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
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

    id: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(always=True))
    request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'local'")
    )
    tool_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    args_hash: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


sa.Index("audit_events_request_idx", AuditEvent.request_id, AuditEvent.created_at.asc())
sa.Index("audit_events_created_idx", AuditEvent.created_at.asc())
