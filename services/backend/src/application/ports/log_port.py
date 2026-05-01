from abc import ABC, abstractmethod
from typing import Any


class LogPort(ABC):
    @abstractmethod
    def publish(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        performed_by: str,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> None: ...
