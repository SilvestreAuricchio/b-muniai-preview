from datetime import date

from src.application.ports.slot_repository import SlotRepository
from src.domain.entities.slot import Slot


class ListSlotsUseCase:
    def __init__(self, repo: SlotRepository) -> None:
        self._repo = repo

    def execute(
        self,
        hospital_uuid: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Slot], int]:
        return self._repo.list_slots(hospital_uuid, from_date, to_date, page, per_page)
