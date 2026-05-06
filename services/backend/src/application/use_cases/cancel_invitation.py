from dataclasses import dataclass
from src.domain.entities.user import User, UserStatus
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort
from src.application.ports.challenge_port import ChallengePort


@dataclass(frozen=True)
class CancelInvitationCommand:
    uuid: str
    performed_by: str
    correlation_id: str


class CancelInvitationUseCase:
    def __init__(self, repo: UserRepository, log: LogPort, challenge: ChallengePort) -> None:
        self._repo      = repo
        self._log       = log
        self._challenge = challenge

    def execute(self, cmd: CancelInvitationCommand) -> User:
        user = self._repo.find_by_uuid(cmd.uuid)
        if user is None:
            raise LookupError(f"User not found: {cmd.uuid!r}")
        if user.status not in (UserStatus.PENDING, UserStatus.PENDING_APPROVAL):
            raise ValueError(f"Cannot cancel: user status is '{user.status.value}'")

        self._challenge.revoke(cmd.uuid)
        previous_status = user.status.value
        user.deactivate()
        updated = self._repo.update(user)

        self._log.publish(
            action="CANCEL_INVITATION",
            entity_type="USER",
            entity_id=updated.uuid,
            performed_by=cmd.performed_by,
            payload={"previousStatus": previous_status},
            correlation_id=cmd.correlation_id,
        )
        return updated
