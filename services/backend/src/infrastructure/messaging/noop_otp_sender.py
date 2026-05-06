import logging
from src.application.ports.otp_sender_port import OTPSenderPort

_log = logging.getLogger(__name__)


class NoOpEmailSender(OTPSenderPort):
    def send(self, uuid: str, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP email → %s  uuid=%s  otp=%s  ttl=%ds  [dev: not sent]", email, uuid, otp, ttl_seconds)


class NoOpWhatsAppSender(OTPSenderPort):
    def send(self, uuid: str, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP whatsapp → %s  uuid=%s  otp=%s  ttl=%ds  [dev: not sent]", telephone, uuid, otp, ttl_seconds)


class NoOpSMSSender(OTPSenderPort):
    def send(self, uuid: str, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP sms → %s  uuid=%s  otp=%s  ttl=%ds  [dev: not sent]", telephone, uuid, otp, ttl_seconds)
