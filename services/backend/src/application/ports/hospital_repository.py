from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.hospital import Hospital, UserHospital


class HospitalRepository(ABC):
    @abstractmethod
    def save(self, hospital: Hospital) -> Hospital: ...

    @abstractmethod
    def find_by_uuid(self, uuid: str) -> Optional[Hospital]: ...

    @abstractmethod
    def find_by_cnpj(self, cnpj: str) -> Optional[Hospital]: ...

    @abstractmethod
    def list_all(self) -> list[Hospital]: ...

    @abstractmethod
    def link_user(self, uh: UserHospital) -> None: ...

    @abstractmethod
    def list_users_for_hospital(self, hospital_uuid: str) -> list[UserHospital]: ...

    @abstractmethod
    def list_by_user(self, user_uuid: str) -> list[Hospital]: ...
