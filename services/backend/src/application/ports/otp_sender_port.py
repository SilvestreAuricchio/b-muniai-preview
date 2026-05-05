from abc import ABC, abstractmethod


class OTPSenderPort(ABC):
    """Single-channel OTP delivery adapter (email, WhatsApp, SMS, …)."""

    @abstractmethod
    def send(self, email: str, telephone: str, otp: str, ttl_seconds: int) -> None:
        """Send OTP via this channel. Raise on failure so the consumer can NACK."""
