from dataclasses import dataclass
from src.domain.entities.user import User
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort
from src.application.ports.notification_port import NotificationPort


@dataclass(frozen=True)
class ApproveUserCommand:
    uuid:           str
    performed_by:   str   # PSA uuid
    correlation_id: str


class ApproveUserUseCase:
    def __init__(self, repo: UserRepository, log: LogPort, notification: NotificationPort) -> None:
        self._repo         = repo
        self._log          = log
        self._notification = notification

    def execute(self, cmd: ApproveUserCommand) -> User:
        user = self._repo.find_by_uuid(cmd.uuid)
        if user is None:
            raise LookupError(f"User not found: {cmd.uuid!r}")

        user.activate()
        updated = self._repo.update(user)

        self._log.publish(
            action="APPROVE_USER",
            entity_type="USER",
            entity_id=updated.uuid,
            performed_by=cmd.performed_by,
            payload={"status": updated.status.value},
            correlation_id=cmd.correlation_id,
        )
        self._notification.notify_activation(
            psa_uuid=cmd.performed_by,
            user_uuid=updated.uuid,
            user_name=updated.name,
            correlation_id=cmd.correlation_id,
        )
        return updated
