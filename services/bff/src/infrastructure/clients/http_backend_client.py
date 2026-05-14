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

    def put(self, path: str, body: dict, headers: dict) -> tuple[dict, int]:
        _log.debug("→ PUT %s  payload=%s", path, body)
        r = requests.put(f"{self._base}{path}", json=body, headers=headers, timeout=self._timeout)
        _log.debug("← PUT %s  status=%s  body=%.300s", path, r.status_code, r.text)
        return _safe_json(r), r.status_code

    def delete(self, path: str, headers: dict) -> tuple[dict, int]:
        _log.debug("→ DELETE %s", path)
        r = requests.delete(f"{self._base}{path}", headers=headers, timeout=self._timeout)
        _log.debug("← DELETE %s  status=%s", path, r.status_code)
        return _safe_json(r), r.status_code

    def post_slot(self, data: dict, headers: dict) -> tuple[dict, int]:
        return self.post("/slots", data, headers)

    def list_slots(self, params: dict, headers: dict) -> tuple[dict, int]:
        _log.debug("→ GET /slots  params=%s", params)
        r = requests.get(f"{self._base}/slots", params=params, headers=headers, timeout=self._timeout)
        _log.debug("← GET /slots  status=%s", r.status_code)
        return _safe_json(r), r.status_code

    def update_slot(self, uuid: str, data: dict, headers: dict) -> tuple[dict, int]:
        return self.put(f"/slots/{uuid}", data, headers)

    def delete_slot(self, uuid: str, headers: dict) -> tuple[dict, int]:
        return self.delete(f"/slots/{uuid}", headers)

    def list_medicineres(self, params: dict, headers: dict) -> tuple[dict, int]:
        _log.debug("→ GET /medicineres  params=%s", params)
        r = requests.get(f"{self._base}/medicineres", params=params, headers=headers, timeout=self._timeout)
        _log.debug("← GET /medicineres  status=%s", r.status_code)
        return _safe_json(r), r.status_code

    def create_mediciner(self, data: dict, headers: dict) -> tuple[dict, int]:
        return self.post("/medicineres", data, headers)

    def get_mediciner(self, uuid: str, headers: dict) -> tuple[dict, int]:
        return self.get(f"/medicineres/{uuid}", headers)

    def update_mediciner(self, uuid: str, data: dict, headers: dict) -> tuple[dict, int]:
        return self.put(f"/medicineres/{uuid}", data, headers)

    def lookup_crm(self, state: str, number: str, headers: dict) -> tuple[dict, int]:
        _log.debug("→ GET /medicineres/crm-lookup  state=%s number=%s", state, number)
        r = requests.get(
            f"{self._base}/medicineres/crm-lookup",
            params={"state": state, "number": number},
            headers=headers,
            timeout=self._timeout,
        )
        _log.debug("← GET /medicineres/crm-lookup  status=%s", r.status_code)
        if r.status_code == 204:
            return {}, 204
        return _safe_json(r), r.status_code
