from src.application.ports.crm_lookup_port import CrmLookupPort


class LookupCrmUseCase:
    def __init__(self, port: CrmLookupPort) -> None:
        self._port = port

    def execute(self, crm_state: str, crm_number: str) -> dict | None:
        return self._port.lookup(crm_state, crm_number)
