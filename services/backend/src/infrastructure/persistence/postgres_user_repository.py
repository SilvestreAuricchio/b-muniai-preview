from typing import Optional

from sqlalchemy import select, insert, update
from sqlalchemy.engine import Engine

from src.application.ports.user_repository import UserRepository
from src.domain.entities.user import User, UserRole, UserStatus, InviteHistory
from src.infrastructure.persistence.schema import app_user_table, invite_history_table


class PostgresUserRepository(UserRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, user: User) -> User:
        with self._engine.begin() as conn:
            conn.execute(insert(app_user_table).values(
                uuid=user.uuid,
                name=user.name,
                telephone=user.telephone,
                email=user.email,
                role=user.role.value,
                status=user.status.value,
                created_at=user.created_at,
                otp_dispatched_at=user.otp_dispatched_at,
                otp_verified_at=user.otp_verified_at,
                activated_at=user.activated_at,
                invite_token=user.invite_token,
            ))
        return user

    def update(self, user: User) -> User:
        with self._engine.begin() as conn:
            conn.execute(
                update(app_user_table)
                .where(app_user_table.c.uuid == user.uuid)
                .values(
                    name=user.name,
                    telephone=user.telephone,
                    email=user.email,
                    role=user.role.value,
                    status=user.status.value,
                    created_at=user.created_at,
                    otp_dispatched_at=user.otp_dispatched_at,
                    otp_verified_at=user.otp_verified_at,
                    activated_at=user.activated_at,
                    invite_token=user.invite_token,
                )
            )
        return user

    def find_by_uuid(self, uuid: str) -> Optional[User]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(app_user_table).where(app_user_table.c.uuid == uuid)
            ).first()
        return self._row_to_user(row) if row else None

    def find_by_email(self, email: str) -> Optional[User]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(app_user_table).where(app_user_table.c.email == email)
            ).first()
        return self._row_to_user(row) if row else None

    def list_all(self) -> list[User]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(app_user_table).order_by(app_user_table.c.created_at.desc())
            ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def save_invite_history(self, record: InviteHistory) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(invite_history_table).values(
                id=record.id,
                user_uuid=record.user_uuid,
                invited_at=record.invited_at,
                otp_dispatched_at=record.otp_dispatched_at,
                otp_verified_at=record.otp_verified_at,
                activated_at=record.activated_at,
            ))

    def list_invite_history(self, user_uuid: str) -> list[InviteHistory]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(invite_history_table)
                .where(invite_history_table.c.user_uuid == user_uuid)
                .order_by(invite_history_table.c.invited_at.asc())
            ).fetchall()
        return [self._row_to_invite_history(r) for r in rows]

    @staticmethod
    def _row_to_invite_history(row) -> InviteHistory:
        return InviteHistory(
            id=row.id,
            user_uuid=row.user_uuid,
            invited_at=row.invited_at,
            otp_dispatched_at=row.otp_dispatched_at,
            otp_verified_at=row.otp_verified_at,
            activated_at=row.activated_at,
        )

    @staticmethod
    def _row_to_user(row) -> User:
        return User(
            uuid=row.uuid,
            name=row.name,
            telephone=row.telephone,
            email=row.email,
            role=UserRole(row.role),
            status=UserStatus(row.status),
            created_at=row.created_at,
            otp_dispatched_at=row.otp_dispatched_at,
            otp_verified_at=row.otp_verified_at,
            activated_at=row.activated_at,
            invite_token=row.invite_token,
        )
