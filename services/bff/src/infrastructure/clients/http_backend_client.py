import logging
import requests
from src.application.ports.backend_client import BackendClient

_log = logging.getLogger(__name__)


def _safe_json(r: requests.Response) -> dict:
    """Parse JSON body; fall back to a plain error dict on HTML/empty responses."""
    try:
        return r.json()
    except ValueError:
        _log.error(
            "Backend returned non-JSON body (status=%s): %.200s",
            r.status_code, r.text,
        )
        return {"error": f"backend error (HTTP {r.status_code})"}


class HttpBackendClient(BackendClient):
    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self._base    = base_url.rstrip("/")
        self._timeout = timeout

    def post(self, path: str, body: dict, headers: dict) -> tuple[dict, int]:
        _log.debug("→ POST %s  payload=%s", path, body)
        r = requests.post(f"{self._base}{path}", json=body, headers=headers, timeout=self._timeout)
        _log.debug("← POST %s  status=%s  body=%.300s", path, r.status_code, r.text)
        return _safe_json(r), r.status_code

    def get(self, path: str, headers: dict) -> tuple[dict, int]:
        _log.debug("→ GET %s", path)
        r = requests.get(f"{self._base}{path}", headers=headers, timeout=self._timeout)
        _log.debug("← GET %s  status=%s", path, r.status_code)
        return _safe_json(r), r.status_code

    def delete(self, path: str, headers: dict) -> tuple[dict, int]:
        _log.debug("→ DELETE %s", path)
        r = requests.delete(f"{self._base}{path}", headers=headers, timeout=self._timeout)
        _log.debug("← DELETE %s  status=%s", path, r.status_code)
        return _safe_json(r), r.status_code
