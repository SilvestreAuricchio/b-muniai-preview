import uuid
from datetime import date, datetime

from src.application.ports.slot_repository import SlotRepository
from src.domain.entities.slot import Slot

_VALID_DEPARTMENTS = {"UTI", "PA", "PS"}
_VALID_TYPES       = {"PM", "PE", "CC", "CM"}


class CreateSlotUseCase:
    def __init__(self, repo: SlotRepository) -> None:
        self._repo = repo

    def execute(
        self,
        hospital_uuid: str,
        department: str,
        slot_type: str,
        slot_date: date,
        created_by: str,
        mediciner_crm: str | None = None,
    ) -> Slot:
        if department not in _VALID_DEPARTMENTS:
            raise ValueError(f"department must be one of {sorted(_VALID_DEPARTMENTS)}")
        if slot_type not in _VALID_TYPES:
            raise ValueError(f"type must be one of {sorted(_VALID_TYPES)}")
        if not isinstance(slot_date, date):
            raise ValueError("date must be a valid date")

        slot = Slot(
            uuid=str(uuid.uuid4()),
            hospital_uuid=hospital_uuid,
            department=department,
            type=slot_type,
            date=slot_date,
            created_by=created_by,
            created_at=datetime.utcnow(),
            mediciner_crm=mediciner_crm or None,
        )
        return self._repo.save(slot)
