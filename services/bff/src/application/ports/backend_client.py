from abc import ABC, abstractmethod
from typing import Any


class BackendClient(ABC):
    @abstractmethod
    def post(self, path: str, body: dict, headers: dict) -> tuple[dict, int]: ...

    @abstractmethod
    def get(self, path: str, headers: dict) -> tuple[dict, int]: ...

    @abstractmethod
    def delete(self, path: str, headers: dict) -> tuple[dict, int]: ...
