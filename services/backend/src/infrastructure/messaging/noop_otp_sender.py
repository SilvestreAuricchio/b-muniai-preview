import logging
from src.application.ports.otp_sender_port import OTPSenderPort

_log = logging.getLogger(__name__)


class NoOpEmailSender(OTPSenderPort):
    def send(self, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP email → %s  otp=%s  ttl=%ds  [dev: not sent]", email, otp, ttl_seconds)


class NoOpWhatsAppSender(OTPSenderPort):
    def send(self, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP whatsapp → %s  otp=%s  ttl=%ds  [dev: not sent]", telephone, otp, ttl_seconds)


class NoOpSMSSender(OTPSenderPort):
    def send(self, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        _log.info("OTP sms → %s  otp=%s  ttl=%ds  [dev: not sent]", telephone, otp, ttl_seconds)
