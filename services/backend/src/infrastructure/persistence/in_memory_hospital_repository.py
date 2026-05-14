from typing import Optional
from src.domain.entities.hospital import Hospital, UserHospital
from src.application.ports.hospital_repository import HospitalRepository


class InMemoryHospitalRepository(HospitalRepository):
    """Dev/test in-memory store. Replace with PostgresHospitalRepository in production."""

    def __init__(self) -> None:
        self._hospitals: dict[str, Hospital] = {}  # uuid → Hospital
        self._links:     list[UserHospital]  = []

    def save(self, hospital: Hospital) -> Hospital:
        self._hospitals[hospital.uuid] = hospital
        return hospital

    def find_by_uuid(self, uuid: str) -> Optional[Hospital]:
        return self._hospitals.get(uuid)

    def find_by_cnpj(self, cnpj: str) -> Optional[Hospital]:
        return next((h for h in self._hospitals.values() if h.cnpj == cnpj), None)

    def list_all(self) -> list[Hospital]:
        return list(self._hospitals.values())

    def link_user(self, uh: UserHospital) -> None:
        self._links.append(uh)

    def list_users_for_hospital(self, hospital_uuid: str) -> list[UserHospital]:
        return [lnk for lnk in self._links if lnk.hospital_uuid == hospital_uuid]

    def list_by_user(self, user_uuid: str) -> list[Hospital]:
        linked_uuids = {lnk.hospital_uuid for lnk in self._links if lnk.user_uuid == user_uuid}
        return [h for h in self._hospitals.values() if h.uuid in linked_uuids]
