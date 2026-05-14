from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.application.ports.slot_repository import SlotRepository
from src.domain.entities.slot import Slot
from src.infrastructure.persistence.schema import slot_table


class PostgresSlotRepository(SlotRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, slot: Slot) -> Slot:
        with self._engine.begin() as conn:
            stmt = pg_insert(slot_table).values(
                uuid=slot.uuid,
                hospital_uuid=slot.hospital_uuid,
                department=slot.department,
                type=slot.type,
                date=slot.date,
                mediciner_crm=slot.mediciner_crm,
                created_by=slot.created_by,
                created_at=slot.created_at,
            ).on_conflict_do_update(
                index_elements=["uuid"],
                set_=dict(
                    department=slot.department,
                    type=slot.type,
                    date=slot.date,
                    mediciner_crm=slot.mediciner_crm,
                ),
            )
            conn.execute(stmt)
        return slot

    def find_by_uuid(self, uuid: str) -> Optional[Slot]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(slot_table).where(slot_table.c.uuid == uuid)
            ).first()
        return self._row_to_slot(row) if row else None

    def list_slots(
        self,
        hospital_uuid: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        per_page: int,
    ) -> tuple[list[Slot], int]:
        base = select(slot_table).order_by(slot_table.c.date)
        count_base = select(func.count()).select_from(slot_table)

        if hospital_uuid is not None:
            base       = base.where(slot_table.c.hospital_uuid == hospital_uuid)
            count_base = count_base.where(slot_table.c.hospital_uuid == hospital_uuid)
        if from_date is not None:
            base       = base.where(slot_table.c.date >= from_date)
            count_base = count_base.where(slot_table.c.date >= from_date)
        if to_date is not None:
            base       = base.where(slot_table.c.date <= to_date)
            count_base = count_base.where(slot_table.c.date <= to_date)

        offset = (page - 1) * per_page
        base   = base.offset(offset).limit(per_page)

        with self._engine.connect() as conn:
            rows  = conn.execute(base).fetchall()
            total = conn.execute(count_base).scalar() or 0

        return [self._row_to_slot(r) for r in rows], total

    def delete(self, uuid: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(sa_delete(slot_table).where(slot_table.c.uuid == uuid))

    @staticmethod
    def _row_to_slot(row) -> Slot:
        return Slot(
            uuid=row.uuid,
            hospital_uuid=row.hospital_uuid,
            department=row.department,
            type=row.type,
            date=row.date,
            mediciner_crm=row.mediciner_crm,
            created_by=row.created_by,
            created_at=row.created_at,
        )
