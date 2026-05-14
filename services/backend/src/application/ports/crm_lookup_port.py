from abc import ABC, abstractmethod


class CrmLookupPort(ABC):
    @abstractmethod
    def lookup(self, crm_state: str, crm_number: str) -> dict | None: ...
    # Returns {"name": ..., "specialty": ..., "situation": ...} or None
