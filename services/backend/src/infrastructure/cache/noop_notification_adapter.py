import logging
from datetime import datetime, timezone
from src.application.ports.notification_port import NotificationPort

_log = logging.getLogger(__name__)


class NoOpNotificationAdapter(NotificationPort):
    """In-memory notification inbox. Events are lost on restart."""

    def __init__(self) -> None:
        self._inbox: dict[str, list[dict]] = {}

    def notify_activation(self, psa_uuid, user_uuid, user_name, correlation_id) -> None:
        self._inbox.setdefault(psa_uuid, []).append({
            "type":          "USER_ACTIVATED",
            "userUuid":      user_uuid,
            "userName":      user_name,
            "correlationId": correlation_id,
            "at":            datetime.now(timezone.utc).isoformat(),
        })
        _log.info("NOTIFICATION psa=%s ← '%s' activated", psa_uuid, user_name)

    def notify_otp_verified(self, psa_uuid, user_uuid, user_name, correlation_id) -> None:
        self._inbox.setdefault(psa_uuid, []).append({
            "type":          "USER_OTP_VERIFIED",
            "userUuid":      user_uuid,
            "userName":      user_name,
            "correlationId": correlation_id,
            "at":            datetime.now(timezone.utc).isoformat(),
        })
        _log.info("NOTIFICATION psa=%s ← '%s' verified OTP — awaiting approval", psa_uuid, user_name)

    def send_activation_email(self, user_email, user_name, correlation_id) -> None:
        _log.info("ACTIVATION EMAIL → %s ('%s')  [dev: not sent]", user_email, user_name)

    def pop_for_psa(self, psa_uuid: str) -> list[dict]:
        return self._inbox.pop(psa_uuid, [])
