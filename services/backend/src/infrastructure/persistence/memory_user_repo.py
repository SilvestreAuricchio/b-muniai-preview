from typing import Optional
from src.domain.entities.user import User, InviteHistory
from src.application.ports.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    """Dev/test in-memory store. Replace with PostgresUserRepository in production."""

    def __init__(self) -> None:
        self._store:   dict[str, User]             = {}
        self._history: dict[str, list[InviteHistory]] = {}

    def save(self, user: User) -> User:
        self._store[user.uuid] = user
        return user

    def update(self, user: User) -> User:
        if user.uuid not in self._store:
            raise LookupError(f"User not found: {user.uuid!r}")
        self._store[user.uuid] = user
        return user

    def find_by_uuid(self, uuid: str) -> Optional[User]:
        return self._store.get(uuid)

    def find_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self._store.values() if u.email == email), None)

    def list_all(self) -> list[User]:
        return list(self._store.values())

    def save_invite_history(self, record: InviteHistory) -> None:
        self._history.setdefault(record.user_uuid, []).append(record)

    def list_invite_history(self, user_uuid: str) -> list[InviteHistory]:
        return sorted(self._history.get(user_uuid, []), key=lambda r: r.invited_at)
