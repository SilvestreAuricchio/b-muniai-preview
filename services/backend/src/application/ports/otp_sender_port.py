from abc import ABC, abstractmethod


class PermanentDeliveryError(Exception):
    """
    Raised when a delivery failure is permanent and retrying will never help
    (e.g. bad credentials, invalid recipient address).
    The consumer will NACK with requeue=False so the message is discarded
    instead of looping forever.
    """


class OTPSenderPort(ABC):
    """Single-channel OTP delivery adapter (email, WhatsApp, SMS, …)."""

    @abstractmethod
    def send(self, uuid: str, email: str, telephone: str, otp: str, ttl_seconds: int, base_url: str = "") -> None:
        """
        Send OTP via this channel.
        base_url: originating host (e.g. https://muninai.com.aw) for activation link; falls back to APP_URL env var.
        Raise PermanentDeliveryError for unrecoverable failures (wrong credentials, etc.).
        Raise any other exception for transient failures (network, timeout) — consumer requeues.
        """
