"""SQLAlchemy Core metadata for the attendance schema."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

SCHEMA = "attendance"
metadata = sa.MetaData(schema=SCHEMA)

attendance_event = sa.Table(
    "attendance_event",
    metadata,
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
    sa.CheckConstraint(
        "direction IN ('IN', 'OUT')",
        name="ck_attendance_event_direction",
    ),
    sa.CheckConstraint(
        "local_sequence >= 0",
        name="ck_attendance_event_local_sequence",
    ),
    sa.CheckConstraint(
        "evidence_level IN ('CONTROLLER_CONFIRMED', 'CONTROLLER_UNCONFIRMED', 'GUARD_RECORDED')",
        name="ck_attendance_event_evidence_level",
    ),
    sa.PrimaryKeyConstraint("event_id", name="pk_attendance_event"),
)
sa.Index(
    "ix_attendance_event_employee_time",
    attendance_event.c.employee_ref,
    attendance_event.c.occurred_at,
    attendance_event.c.event_id,
)
sa.Index(
    "ix_attendance_event_station_time",
    attendance_event.c.station_id,
    attendance_event.c.occurred_at,
)

event_conflict = sa.Table(
    "event_conflict",
    metadata,
    sa.Column("conflict_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("station_id", sa.String(64), nullable=False),
    sa.Column("kind", sa.Text(), nullable=False),
    sa.Column("incoming_payload", postgresql.JSONB(), nullable=False),
    sa.Column("incoming_hash", sa.CHAR(64), nullable=False),
    sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "kind IN ('PAYLOAD_MISMATCH')",
        name="ck_event_conflict_kind",
    ),
    sa.PrimaryKeyConstraint("conflict_id", name="pk_event_conflict"),
    sa.UniqueConstraint(
        "event_id",
        "kind",
        "incoming_hash",
        name="uq_event_conflict_once",
    ),
)
sa.Index(
    "ix_event_conflict_station_time",
    event_conflict.c.station_id,
    event_conflict.c.detected_at,
)

outbox = sa.Table(
    "outbox",
    metadata,
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
    sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint(
        "state IN ('PENDING', 'PUBLISHED', 'FAILED')",
        name="ck_outbox_state",
    ),
    sa.PrimaryKeyConstraint("message_id", name="pk_outbox"),
)
sa.Index(
    "ix_outbox_pending",
    outbox.c.occurred_at,
    postgresql_where=sa.text("state = 'PENDING'"),
)
