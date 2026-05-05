from abc import ABC, abstractmethod


class NotificationPort(ABC):
    @abstractmethod
    def notify_activation(
        self,
        psa_uuid: str,
        user_uuid: str,
        user_name: str,
        correlation_id: str,
    ) -> None: ...

    @abstractmethod
    def notify_otp_verified(
        self,
        psa_uuid: str,
        user_uuid: str,
        user_name: str,
        correlation_id: str,
    ) -> None: ...

    @abstractmethod
    def pop_for_psa(self, psa_uuid: str) -> list[dict]: ...
