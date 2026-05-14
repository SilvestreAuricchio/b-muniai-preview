import redis as redis_lib

_REVOKED = "REVOKED"


class InviteTokenCache:
    """
    Stores session revocation state in Redis DB 2.

    Two complementary keys per user:
      itk:{uuid}      — invite token for itk-claim validation (new sessions)
      blocked:{email} — email blocklist for legacy sessions without itk claim

    The email key covers existing JWTs issued before the itk system existed,
    ensuring immediate revocation for ALL sessions including bootstrap SAs.
    """

    def __init__(self, redis_url: str) -> None:
        self._r = redis_lib.from_url(redis_url, decode_responses=True)

    def set(self, uuid: str, token: str) -> None:
        self._r.set(f"itk:{uuid}", token)

    def activate(self, uuid: str, email: str, token: str) -> None:
        """Set itk token AND clear email block — used on approve_user."""
        self._r.set(f"itk:{uuid}", token)
        self._r.delete(f"blocked:{email}")

    def revoke(self, uuid: str, email: str) -> None:
        self._r.set(f"itk:{uuid}", _REVOKED)
        self._r.set(f"blocked:{email}", "1")

    def unblock(self, uuid: str, email: str) -> None:
        self._r.set(f"itk:{uuid}", _REVOKED)   # itk stays revoked until re-approve
        self._r.delete(f"blocked:{email}")
