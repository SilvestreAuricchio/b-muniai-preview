import secrets
import uuid as _uuid
from dataclasses import dataclass
from typing import Optional
from src.domain.entities.user import User, UserRole, UserStatus, InviteHistory
from src.domain.entities.hospital import UserHospital
from src.application.ports.user_repository import UserRepository
from src.application.ports.hospital_repository import HospitalRepository
from src.application.ports.log_port import LogPort
from src.application.ports.challenge_port import ChallengePort

OTP_TTL_SECONDS = 345_600  # 4 days per spec


@dataclass(frozen=True)
class CreateUserCommand:
    name:           str
    telephone:      str
    email:          str
    role:           UserRole
    performed_by:   str        # PSA uuid
    correlation_id: str
    base_url:       str = ""   # originating host for OTP activation link
    hospital_uuid:  str = ""   # Scheduler only — pre-created hospital UUID


@dataclass(frozen=True)
class CreateUserResult:
    user: User
    otp: str            # returned for dev use (channel = None)
    otp_ttl_seconds: int


class CreateUserUseCase:
    def __init__(
        self,
        repo:          UserRepository,
        log:           LogPort,
        challenge:     ChallengePort,
        hospital_repo: Optional[HospitalRepository] = None,
    ) -> None:
        self._repo          = repo
        self._log           = log
        self._challenge     = challenge
        self._hospital_repo = hospital_repo

    def execute(self, cmd: CreateUserCommand) -> CreateUserResult:
        existing = self._repo.find_by_email(cmd.email)
        if existing:
            if existing.status != UserStatus.INACTIVE:
                raise ValueError(f"Email already registered: {cmd.email!r}")
            self._repo.save_invite_history(InviteHistory(
                id=str(_uuid.uuid4()),
                user_uuid=existing.uuid,
                invited_at=existing.created_at,
                otp_dispatched_at=existing.otp_dispatched_at,
                otp_verified_at=existing.otp_verified_at,
                activated_at=existing.activated_at,
            ))
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
            base_url=cmd.base_url,
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

        if cmd.role == UserRole.SCHEDULER and cmd.hospital_uuid and self._hospital_repo:
            uh = UserHospital(
                user_uuid=saved.uuid,
                hospital_uuid=cmd.hospital_uuid,
                scope="Scheduler",
            )
            self._hospital_repo.link_user(uh)
            self._log.publish(
                action="LINK_USER_HOSPITAL",
                entity_type="USER_HOSPITAL",
                entity_id=f"{saved.uuid}:{cmd.hospital_uuid}",
                performed_by=cmd.performed_by,
                payload={"user_uuid": saved.uuid, "hospital_uuid": cmd.hospital_uuid, "scope": "Scheduler"},
                correlation_id=cmd.correlation_id,
            )

        return CreateUserResult(user=saved, otp=otp, otp_ttl_seconds=OTP_TTL_SECONDS)
