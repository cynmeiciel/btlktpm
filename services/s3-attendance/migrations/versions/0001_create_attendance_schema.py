"""Create the initial attendance tables, indexes, view, and permissions.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "attendance"


def _create_attendance_event_table() -> None:
    op.create_table(
        "attendance_event",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_ref", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(64), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_sequence", sa.BigInteger(), nullable=False),
        sa.Column("evidence_level", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("payload_hash", sa.CHAR(64), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name="pk_attendance_event"),
        sa.CheckConstraint(
            "direction IN ('IN', 'OUT')",
            name="ck_attendance_event_direction",
        ),
        sa.CheckConstraint(
            "local_sequence >= 0",
            name="ck_attendance_event_local_sequence",
        ),
        sa.CheckConstraint(
            "evidence_level IN "
            "('CONTROLLER_CONFIRMED', "
            "'CONTROLLER_UNCONFIRMED', "
            "'GUARD_RECORDED')",
            name="ck_attendance_event_evidence_level",
        ),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_attendance_event_employee_time",
        "attendance_event",
        ["employee_ref", "occurred_at", "event_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_attendance_event_station_time",
        "attendance_event",
        ["station_id", "occurred_at"],
        schema=SCHEMA,
    )


def _create_event_conflict_table() -> None:
    op.create_table(
        "event_conflict",
        sa.Column("conflict_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("incoming_payload", postgresql.JSONB(), nullable=False),
        sa.Column("incoming_hash", sa.CHAR(64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("conflict_id", name="pk_event_conflict"),
        sa.UniqueConstraint(
            "event_id",
            "kind",
            "incoming_hash",
            name="uq_event_conflict_once",
        ),
        sa.CheckConstraint(
            "kind IN ('PAYLOAD_MISMATCH')",
            name="ck_event_conflict_kind",
        ),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_event_conflict_station_time",
        "event_conflict",
        ["station_id", "detected_at"],
        schema=SCHEMA,
    )


def _create_outbox_table() -> None:
    op.create_table(
        "outbox",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "state",
            sa.Text(),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("message_id", name="pk_outbox"),
        sa.CheckConstraint(
            "state IN ('PENDING', 'PUBLISHED', 'FAILED')",
            name="ck_outbox_state",
        ),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["occurred_at"],
        schema=SCHEMA,
        postgresql_where=sa.text("state = 'PENDING'"),
    )


def _create_reporting_view() -> None:
    op.execute(
        f"""
        CREATE VIEW {SCHEMA}.v1_attendance_event AS
        SELECT
            event_id,
            employee_ref,
            station_id,
            direction,
            occurred_at,
            received_at,
            evidence_level
        FROM {SCHEMA}.attendance_event
        """
    )


def _grant_table_permissions() -> None:
    op.execute(
        f"GRANT SELECT, INSERT ON {SCHEMA}.attendance_event "
        "TO s3_attendance_app"
    )
    op.execute(
        f"GRANT SELECT, INSERT ON {SCHEMA}.event_conflict "
        "TO s3_attendance_app"
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE ON {SCHEMA}.outbox "
        "TO s3_attendance_app"
    )
    op.execute(
        f"GRANT SELECT ON {SCHEMA}.v1_attendance_event "
        "TO s4_reporting_reader"
    )


def upgrade() -> None:
    """Create the tables, indexes, view, and database permissions."""
    _create_attendance_event_table()
    _create_event_conflict_table()
    _create_outbox_table()
    _create_reporting_view()
    _grant_table_permissions()


def downgrade() -> None:
    """Remove the objects created by this migration."""
    op.execute(f"DROP VIEW {SCHEMA}.v1_attendance_event")

    op.drop_index(
        "ix_outbox_pending",
        table_name="outbox",
        schema=SCHEMA,
    )
    op.drop_table("outbox", schema=SCHEMA)

    op.drop_index(
        "ix_event_conflict_station_time",
        table_name="event_conflict",
        schema=SCHEMA,
    )
    op.drop_table("event_conflict", schema=SCHEMA)

    op.drop_index(
        "ix_attendance_event_station_time",
        table_name="attendance_event",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_attendance_event_employee_time",
        table_name="attendance_event",
        schema=SCHEMA,
    )
    op.drop_table("attendance_event", schema=SCHEMA)
