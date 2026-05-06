import secrets
from dataclasses import dataclass
from src.domain.entities.user import User, UserRole, UserStatus
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort
from src.application.ports.challenge_port import ChallengePort

OTP_TTL_SECONDS = 345_600  # 4 days per spec


@dataclass(frozen=True)
class CreateUserCommand:
    name: str
    telephone: str
    email: str
    role: UserRole
    performed_by: str   # PSA uuid
    correlation_id: str


@dataclass(frozen=True)
class CreateUserResult:
    user: User
    otp: str            # returned for dev use (channel = None)
    otp_ttl_seconds: int


class CreateUserUseCase:
    def __init__(self, repo: UserRepository, log: LogPort, challenge: ChallengePort) -> None:
        self._repo      = repo
        self._log       = log
        self._challenge = challenge

    def execute(self, cmd: CreateUserCommand) -> CreateUserResult:
        existing = self._repo.find_by_email(cmd.email)
        if existing:
            if existing.status != UserStatus.INACTIVE:
                raise ValueError(f"Email already registered: {cmd.email!r}")
            # Re-invitation of a previously cancelled user: reset and reuse record
            existing.reinvite(cmd.name, cmd.telephone, cmd.role)
            saved = self._repo.update(existing)
        else:
            user  = User.create(cmd.name, cmd.telephone, cmd.email, cmd.role)
            saved = self._repo.save(user)

        otp = f"{secrets.randbelow(1_000_000):06d}"
        self._challenge.issue(
            uuid=saved.uuid,
            email=cmd.email,
            telephone=cmd.telephone,
            otp=otp,
            psa_uuid=cmd.performed_by,
            ttl_seconds=OTP_TTL_SECONDS,
        )
        saved.mark_otp_dispatched()
        self._repo.update(saved)

        self._log.publish(
            action="CREATE_USER",
            entity_type="USER",
            entity_id=saved.uuid,
            performed_by=cmd.performed_by,
            payload={"name": cmd.name, "email": cmd.email, "role": cmd.role.value},
            correlation_id=cmd.correlation_id,
        )

        return CreateUserResult(user=saved, otp=otp, otp_ttl_seconds=OTP_TTL_SECONDS)
