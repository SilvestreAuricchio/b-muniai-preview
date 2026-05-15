from src.domain.entities.hospital import Hospital
from src.application.ports.hospital_repository import HospitalRepository


class GetHospitalUseCase:
    def __init__(self, repo: HospitalRepository) -> None:
        self._repo = repo

    def execute(self, uuid: str) -> Hospital:
        hospital = self._repo.find_by_uuid(uuid)
        if hospital is None:
            raise LookupError(f"Hospital not found: {uuid!r}")
        return hospital
