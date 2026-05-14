from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.application.ports.mediciner_repository import MedicineerRepository
from src.domain.entities.mediciner import MedicineerProfile
from src.infrastructure.persistence.schema import (
    mediciner_profile_table,
    app_user_table,
)


class PostgresMedicineerRepository(MedicineerRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_profile(self, profile: MedicineerProfile) -> MedicineerProfile:
        with self._engine.begin() as conn:
            conn.execute(insert(mediciner_profile_table).values(
                user_uuid=profile.user_uuid,
                cpf=profile.cpf,
                email=profile.email,
                specialty=profile.specialty,
                crm_state=profile.crm_state,
                crm_number=profile.crm_number,
            ))
        return profile

    def find_profile_by_user_uuid(self, user_uuid: str) -> MedicineerProfile | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(mediciner_profile_table).where(
                    mediciner_profile_table.c.user_uuid == user_uuid
                )
            ).first()
        return self._row_to_profile(row) if row else None

    def list_profiles(
        self, page: int, per_page: int, search: str | None
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * per_page
        base = (
            select(
                app_user_table.c.uuid,
                app_user_table.c.name,
                app_user_table.c.telephone,
                app_user_table.c.status,
                app_user_table.c.created_at,
                mediciner_profile_table.c.cpf,
                mediciner_profile_table.c.email,
                mediciner_profile_table.c.specialty,
                mediciner_profile_table.c.crm_state,
                mediciner_profile_table.c.crm_number,
            )
            .join(
                mediciner_profile_table,
                mediciner_profile_table.c.user_uuid == app_user_table.c.uuid,
            )
        )

        if search:
            term = f"%{search}%"
            from sqlalchemy import or_
            base = base.where(
                or_(
                    app_user_table.c.name.ilike(term),
                    mediciner_profile_table.c.cpf.ilike(term),
                )
            )

        with self._engine.connect() as conn:
            from sqlalchemy import func, select as sa_select
            count_stmt = sa_select(func.count()).select_from(base.subquery())
            total = conn.execute(count_stmt).scalar() or 0

            rows = conn.execute(
                base.order_by(app_user_table.c.created_at.desc())
                .limit(per_page)
                .offset(offset)
            ).fetchall()

        results = [self._row_to_combined_dict(r) for r in rows]
        return results, total

    def update_profile(self, profile: MedicineerProfile) -> MedicineerProfile:
        with self._engine.begin() as conn:
            conn.execute(
                update(mediciner_profile_table)
                .where(mediciner_profile_table.c.user_uuid == profile.user_uuid)
                .values(
                    specialty=profile.specialty,
                    crm_state=profile.crm_state,
                    crm_number=profile.crm_number,
                )
            )
        return profile

    @staticmethod
    def _row_to_profile(row) -> MedicineerProfile:
        return MedicineerProfile(
            user_uuid=row.user_uuid,
            cpf=row.cpf,
            email=row.email,
            specialty=row.specialty,
            crm_state=row.crm_state,
            crm_number=row.crm_number,
        )

    @staticmethod
    def _row_to_combined_dict(row) -> dict:
        def _iso(dt):
            return dt.isoformat() if dt else None
        return {
            "uuid":       row.uuid,
            "name":       row.name,
            "telephone":  row.telephone,
            "status":     row.status,
            "created_at": _iso(row.created_at),
            "cpf":        row.cpf,
            "email":      row.email,
            "specialty":  row.specialty,
            "crm_state":  row.crm_state,
            "crm_number": row.crm_number,
            "role":       "Mediciner",
        }
