from abc import ABC, abstractmethod
from src.domain.entities.mediciner import MedicineerProfile


class MedicineerRepository(ABC):
    @abstractmethod
    def save_profile(self, profile: MedicineerProfile) -> MedicineerProfile: ...

    @abstractmethod
    def find_profile_by_user_uuid(self, user_uuid: str) -> MedicineerProfile | None: ...

    @abstractmethod
    def list_profiles(
        self, page: int, per_page: int, search: str | None
    ) -> tuple[list[dict], int]: ...

    @abstractmethod
    def update_profile(self, profile: MedicineerProfile) -> MedicineerProfile: ...
