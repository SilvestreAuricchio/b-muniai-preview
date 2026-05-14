from datetime import date

from src.application.ports.slot_repository import SlotRepository
from src.domain.entities.slot import Slot

_VALID_DEPARTMENTS = {"UTI", "PA", "PS"}
_VALID_TYPES       = {"PM", "PE", "CC", "CM"}
UNSET = object()


class UpdateSlotUseCase:
    def __init__(self, repo: SlotRepository) -> None:
        self._repo = repo

    def execute(
        self,
        uuid: str,
        department: str | None = None,
        slot_type: str | None = None,
        slot_date: date | None = None,
        mediciner_crm: object = UNSET,
    ) -> Slot:
        slot = self._repo.find_by_uuid(uuid)
        if slot is None:
            raise LookupError(f"slot {uuid} not found")

        new_department = slot.department
        new_type       = slot.type
        new_date       = slot.date
        new_crm        = slot.mediciner_crm

        if department is not None:
            if department not in _VALID_DEPARTMENTS:
                raise ValueError(f"department must be one of {sorted(_VALID_DEPARTMENTS)}")
            new_department = department

        if slot_type is not None:
            if slot_type not in _VALID_TYPES:
                raise ValueError(f"type must be one of {sorted(_VALID_TYPES)}")
            new_type = slot_type

        if slot_date is not None:
            new_date = slot_date

        if mediciner_crm is not UNSET:
            new_crm = mediciner_crm  # type: ignore[assignment]

        updated = Slot(
            uuid=slot.uuid,
            hospital_uuid=slot.hospital_uuid,
            department=new_department,
            type=new_type,
            date=new_date,
            created_by=slot.created_by,
            created_at=slot.created_at,
            mediciner_crm=new_crm,
        )
        return self._repo.save(updated)
