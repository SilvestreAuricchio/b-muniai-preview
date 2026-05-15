from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.application.ports.hospital_repository import HospitalRepository
from src.domain.entities.hospital import Hospital, SlotType, UserHospital
from src.infrastructure.persistence.schema import hospital_table, user_hospital_table


class PostgresHospitalRepository(HospitalRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, hospital: Hospital) -> Hospital:
        with self._engine.begin() as conn:
            stmt = pg_insert(hospital_table).values(
                uuid=hospital.uuid,
                cnpj=hospital.cnpj,
                name=hospital.name,
                address=hospital.address,
                slot_types=[s.value for s in hospital.slot_types],
            ).on_conflict_do_update(
                index_elements=["uuid"],
                set_=dict(
                    cnpj=hospital.cnpj,
                    name=hospital.name,
                    address=hospital.address,
                    slot_types=[s.value for s in hospital.slot_types],
                ),
            )
            conn.execute(stmt)
        return hospital

    def find_by_uuid(self, uuid: str) -> Optional[Hospital]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(hospital_table).where(hospital_table.c.uuid == uuid)
            ).first()
        return self._row_to_hospital(row) if row else None

    def find_by_cnpj(self, cnpj: str) -> Optional[Hospital]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(hospital_table).where(hospital_table.c.cnpj == cnpj)
            ).first()
        return self._row_to_hospital(row) if row else None

    def list_all(self) -> list[Hospital]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(hospital_table).order_by(hospital_table.c.name)
            ).fetchall()
        return [self._row_to_hospital(r) for r in rows]

    def link_user(self, uh: UserHospital) -> None:
        with self._engine.begin() as conn:
            stmt = pg_insert(user_hospital_table).values(
                user_uuid=uh.user_uuid,
                hospital_uuid=uh.hospital_uuid,
                scope=uh.scope,
            ).on_conflict_do_nothing()
            conn.execute(stmt)

    def list_by_user(self, user_uuid: str) -> list[Hospital]:
        with self._engine.connect() as conn:
            stmt = (
                select(hospital_table)
                .join(
                    user_hospital_table,
                    user_hospital_table.c.hospital_uuid == hospital_table.c.uuid,
                )
                .where(user_hospital_table.c.user_uuid == user_uuid)
                .order_by(hospital_table.c.name)
            )
            rows = conn.execute(stmt).fetchall()
        return [self._row_to_hospital(r) for r in rows]

    def list_users_for_hospital(self, hospital_uuid: str) -> list[UserHospital]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(user_hospital_table).where(
                    user_hospital_table.c.hospital_uuid == hospital_uuid
                )
            ).fetchall()
        return [self._row_to_user_hospital(r) for r in rows]

    @staticmethod
    def _row_to_hospital(row) -> Hospital:
        return Hospital(
            uuid=row.uuid,
            cnpj=row.cnpj,
            name=row.name,
            address=row.address,
            slot_types=[SlotType(s) for s in (row.slot_types or [])],
        )

    @staticmethod
    def _row_to_user_hospital(row) -> UserHospital:
        return UserHospital(
            user_uuid=row.user_uuid,
            hospital_uuid=row.hospital_uuid,
            scope=row.scope,
        )
