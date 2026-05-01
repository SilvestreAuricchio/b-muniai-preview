import requests
from src.application.ports.backend_client import BackendClient


class HttpBackendClient(BackendClient):
    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def post(self, path: str, body: dict, headers: dict) -> tuple[dict, int]:
        r = requests.post(f"{self._base}{path}", json=body, headers=headers, timeout=self._timeout)
        return r.json(), r.status_code

    def get(self, path: str, headers: dict) -> tuple[dict, int]:
        r = requests.get(f"{self._base}{path}", headers=headers, timeout=self._timeout)
        return r.json(), r.status_code
