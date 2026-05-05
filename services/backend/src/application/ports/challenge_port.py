from abc import ABC, abstractmethod


class ChallengePort(ABC):
    @abstractmethod
    def issue(
        self,
        uuid: str,
        email: str,
        telephone: str,
        otp: str,
        psa_uuid: str,
        ttl_seconds: int,
    ) -> None: ...

    @abstractmethod
    def verify(self, uuid: str, otp: str) -> str | None:
        """Returns psa_uuid if OTP is valid and not expired; None otherwise."""

    @abstractmethod
    def revoke(self, uuid: str) -> None: ...
