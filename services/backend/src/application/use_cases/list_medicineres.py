from dataclasses import dataclass
from src.application.ports.mediciner_repository import MedicineerRepository


@dataclass(frozen=True)
class ListMedicineresCommand:
    page:     int = 1
    per_page: int = 20
    search:   str | None = None


class ListMedicineresUseCase:
    def __init__(self, repo: MedicineerRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ListMedicineresCommand) -> tuple[list[dict], int]:
        return self._repo.list_profiles(cmd.page, cmd.per_page, cmd.search or None)
