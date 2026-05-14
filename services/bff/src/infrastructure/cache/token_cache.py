import redis as redis_lib


class TokenCache:
    """
    Read-only view of revocation state written by the backend (Redis DB 2).

    Two checks per request:
      get(uuid)              — itk claim validation for new sessions
      is_email_blocked(email) — email blocklist for legacy sessions without itk claim
    """

    def __init__(self, redis_url: str) -> None:
        self._r = redis_lib.from_url(redis_url, decode_responses=True)

    def get(self, uuid: str) -> str | None:
        return self._r.get(f"itk:{uuid}")

    def is_email_blocked(self, email: str) -> bool:
        return self._r.exists(f"blocked:{email}") == 1
