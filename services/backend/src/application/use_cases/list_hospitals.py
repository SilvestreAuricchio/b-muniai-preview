from dataclasses import dataclass
from src.domain.entities.hospital import Hospital
from src.application.ports.hospital_repository import HospitalRepository


@dataclass(frozen=True)
class ListHospitalsResult:
    hospitals:        list[Hospital]
    scheduler_counts: dict[str, int]   # hospital_uuid → count of linked Schedulers


class ListHospitalsUseCase:
    def __init__(self, repo: HospitalRepository) -> None:
        self._repo = repo

    def execute(self, user_uuid: str | None = None) -> ListHospitalsResult:
        hospitals = (
            self._repo.list_by_user(user_uuid)
            if user_uuid is not None
            else self._repo.list_all()
        )
        counts    = {
            h.uuid: sum(
                1 for lnk in self._repo.list_users_for_hospital(h.uuid)
                if lnk.scope == "Scheduler"
            )
            for h in hospitals
        }
        return ListHospitalsResult(hospitals=hospitals, scheduler_counts=counts)
