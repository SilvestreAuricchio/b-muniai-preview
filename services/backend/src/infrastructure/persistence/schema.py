from sqlalchemy import (
    MetaData, Table, Column, String, DateTime, Date,
    ForeignKey, PrimaryKeyConstraint, text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Engine

metadata = MetaData()

app_user_table = Table(
    "app_user", metadata,
    Column("uuid",              String(36),              primary_key=True),
    Column("name",              String(255),             nullable=False),
    Column("telephone",         String(50),              nullable=False),
    Column("email",             String(255),             nullable=False, unique=True),
    Column("role",              String(20),              nullable=False),
    Column("status",            String(30),              nullable=False),
    Column("created_at",        DateTime(timezone=True), nullable=False),
    Column("otp_dispatched_at", DateTime(timezone=True), nullable=True),
    Column("otp_verified_at",   DateTime(timezone=True), nullable=True),
    Column("activated_at",      DateTime(timezone=True), nullable=True),
    Column("invite_token",      String(36),              nullable=True),
)

hospital_table = Table(
    "hospital", metadata,
    Column("uuid",       String(36),    primary_key=True),
    Column("cnpj",       String(14),    nullable=False, unique=True),
    Column("name",       String(255),   nullable=False),
    Column("address",    String,        nullable=False),
    Column("slot_types", ARRAY(String), nullable=False, server_default="{}"),
)

user_hospital_table = Table(
    "user_hospital", metadata,
    Column("user_uuid",     String(36), ForeignKey("app_user.uuid"),  nullable=False),
    Column("hospital_uuid", String(36), ForeignKey("hospital.uuid"),  nullable=False),
    Column("scope",         String(20), nullable=False),
    PrimaryKeyConstraint("user_uuid", "hospital_uuid"),
)

invite_history_table = Table(
    "invite_history", metadata,
    Column("id",               String(36),              primary_key=True),
    Column("user_uuid",        String(36), ForeignKey("app_user.uuid"), nullable=False),
    Column("invited_at",       DateTime(timezone=True), nullable=False),
    Column("otp_dispatched_at", DateTime(timezone=True), nullable=True),
    Column("otp_verified_at",   DateTime(timezone=True), nullable=True),
    Column("activated_at",      DateTime(timezone=True), nullable=True),
)


mediciner_profile_table = Table(
    "mediciner_profile", metadata,
    Column("user_uuid",   String(36),   ForeignKey("app_user.uuid"), primary_key=True),
    Column("cpf",         String(11),   nullable=False, unique=True),
    Column("email",       String(255),  nullable=False, unique=True),
    Column("specialty",   String(100),  nullable=True),
    Column("crm_state",   String(2),    nullable=True),
    Column("crm_number",  String(20),   nullable=True),
)

slot_table = Table(
    "slot", metadata,
    Column("uuid",          String(36),  primary_key=True),
    Column("hospital_uuid", String(36),  ForeignKey("hospital.uuid"), nullable=False),
    Column("department",    String(3),   nullable=False),
    Column("type",          String(2),   nullable=False),
    Column("date",          Date(),      nullable=False),
    Column("mediciner_crm", String(20),  nullable=True),
    Column("created_by",    String(36),  ForeignKey("app_user.uuid"), nullable=False),
    Column("created_at",    DateTime(),  nullable=False),
)


def create_schema(engine: Engine) -> None:
    metadata.create_all(engine)
    # Add columns that may be missing from existing tables (idempotent)
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE app_user ADD COLUMN IF NOT EXISTS invite_token VARCHAR(36)"
        ))
