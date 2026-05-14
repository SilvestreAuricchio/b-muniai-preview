from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.user import User, InviteHistory


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def find_by_uuid(self, uuid: str) -> Optional[User]: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def list_all(self) -> list[User]: ...

    @abstractmethod
    def save_invite_history(self, record: InviteHistory) -> None: ...

    @abstractmethod
    def list_invite_history(self, user_uuid: str) -> list[InviteHistory]: ...
