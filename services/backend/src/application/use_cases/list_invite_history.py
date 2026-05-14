from dataclasses import dataclass
from src.domain.entities.user import InviteHistory
from src.application.ports.user_repository import UserRepository


@dataclass(frozen=True)
class ListInviteHistoryResult:
    records: list[InviteHistory]


class ListInviteHistoryUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, user_uuid: str) -> ListInviteHistoryResult:
        user = self._repo.find_by_uuid(user_uuid)
        if user is None:
            raise LookupError(f"User not found: {user_uuid!r}")
        return ListInviteHistoryResult(records=self._repo.list_invite_history(user_uuid))
