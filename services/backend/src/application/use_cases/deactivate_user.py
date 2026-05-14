from dataclasses import dataclass
from src.domain.entities.user import User
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort


@dataclass(frozen=True)
class DeactivateUserCommand:
    uuid:           str
    performed_by:   str
    correlation_id: str


class DeactivateUserUseCase:
    def __init__(self, repo: UserRepository, log: LogPort) -> None:
        self._repo = repo
        self._log  = log

    def execute(self, cmd: DeactivateUserCommand) -> User:
        user = self._repo.find_by_uuid(cmd.uuid)
        if user is None:
            raise LookupError(f"User not found: {cmd.uuid!r}")

        user.deactivate()
        saved = self._repo.update(user)

        self._log.publish(
            action="DEACTIVATE_USER",
            entity_type="USER",
            entity_id=saved.uuid,
            performed_by=cmd.performed_by,
            payload={"email": saved.email},
            correlation_id=cmd.correlation_id,
        )

        return saved
