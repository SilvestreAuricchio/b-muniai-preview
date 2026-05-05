from dataclasses import dataclass
from src.domain.entities.user import User
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort
from src.application.ports.challenge_port import ChallengePort
from src.application.ports.notification_port import NotificationPort


@dataclass(frozen=True)
class VerifyOTPCommand:
    uuid:           str
    otp:            str
    correlation_id: str


class VerifyOTPUseCase:
    def __init__(
        self,
        repo:         UserRepository,
        log:          LogPort,
        challenge:    ChallengePort,
        notification: NotificationPort,
    ) -> None:
        self._repo         = repo
        self._log          = log
        self._challenge    = challenge
        self._notification = notification

    def execute(self, cmd: VerifyOTPCommand) -> User:
        user = self._repo.find_by_uuid(cmd.uuid)
        if user is None:
            raise LookupError(f"User not found: {cmd.uuid!r}")

        psa_uuid = self._challenge.verify(cmd.uuid, cmd.otp)
        if psa_uuid is None:
            raise ValueError("Invalid or expired OTP")

        user.verify_otp()
        updated = self._repo.update(user)
        self._challenge.revoke(cmd.uuid)

        self._notification.notify_otp_verified(
            psa_uuid=psa_uuid,
            user_uuid=updated.uuid,
            user_name=updated.name,
            correlation_id=cmd.correlation_id,
        )

        self._log.publish(
            action="VERIFY_OTP",
            entity_type="USER",
            entity_id=updated.uuid,
            performed_by=updated.uuid,
            payload={"status": updated.status.value},
            correlation_id=cmd.correlation_id,
        )
        return updated
