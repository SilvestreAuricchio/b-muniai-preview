from abc import ABC, abstractmethod


class AuditPublisherPort(ABC):
    @abstractmethod
    def publish_hospital_change(self, payload: dict) -> None: ...
