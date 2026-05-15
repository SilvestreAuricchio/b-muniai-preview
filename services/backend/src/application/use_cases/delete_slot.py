from src.application.ports.slot_repository import SlotRepository


class DeleteSlotUseCase:
    def __init__(self, repo: SlotRepository) -> None:
        self._repo = repo

    def execute(self, uuid: str) -> None:
        if self._repo.find_by_uuid(uuid) is None:
            raise LookupError(f"slot {uuid} not found")
        self._repo.delete(uuid)
