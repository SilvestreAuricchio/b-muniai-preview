import time
import logging
from src.application.ports.challenge_port import ChallengePort

_log = logging.getLogger(__name__)


class NoOpOTPAdapter(ChallengePort):
    """
    In-memory OTP store for dev/test.
    Production: replace with RabbitMQOTPPublisher (stores in Redis; dispatches
    via async consumer to email + WhatsApp + SMS).
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def issue(self, uuid, email, telephone, otp, psa_uuid, ttl_seconds, base_url: str = "") -> None:
        self._store[uuid] = {
            "otp":      otp,
            "psa_uuid": psa_uuid,
            "expiry":   time.monotonic() + ttl_seconds,
        }
        _log.info(
            "CHALLENGE issued uuid=%s email=%s otp=%s ttl=%ds "
            "[dev: would dispatch to email+WhatsApp+SMS via async consumer]",
            uuid, email, otp, ttl_seconds,
        )

    def verify(self, uuid: str, otp: str) -> str | None:
        entry = self._store.get(uuid)
        if entry is None:
            return None
        if time.monotonic() > entry["expiry"]:
            self._store.pop(uuid, None)
            return None
        if entry["otp"] != otp:
            return None
        return entry["psa_uuid"]

    def revoke(self, uuid: str) -> None:
        self._store.pop(uuid, None)
        _log.info("CHALLENGE revoked uuid=%s", uuid)
