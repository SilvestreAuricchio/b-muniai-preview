from abc import ABC, abstractmethod
from datetime import date
from src.domain.entities.slot import Slot


class SlotRepository(ABC):
    @abstractmethod
    def save(self, slot: Slot) -> Slot: ...

    @abstractmethod
    def find_by_uuid(self, uuid: str) -> Slot | None: ...

    @abstractmethod
    def list_slots(
        self,
        hospital_uuid: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        per_page: int,
    ) -> tuple[list[Slot], int]: ...

    @abstractmethod
    def delete(self, uuid: str) -> None: ...
