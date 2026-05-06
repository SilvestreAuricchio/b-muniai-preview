from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid as _uuid


class UserRole(str, Enum):
    SA_ROOT   = "SA-root"
    SCHEDULER = "Scheduler"
    MEDICINER = "Mediciner"


class UserStatus(str, Enum):
    PENDING          = "pending"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE           = "active"
    INACTIVE         = "inactive"


@dataclass
class User:
    uuid:              str
    name:              str
    telephone:         str
    email:             str
    role:              UserRole
    status:            UserStatus
    created_at:        datetime        = field(default_factory=lambda: datetime.now(timezone.utc))
    otp_dispatched_at: datetime | None = field(default=None)
    otp_verified_at:   datetime | None = field(default=None)
    activated_at:      datetime | None = field(default=None)

    @classmethod
    def create(cls, name: str, telephone: str, email: str, role: UserRole) -> "User":
        return cls(
            uuid=str(_uuid.uuid4()),
            name=name,
            telephone=telephone,
            email=email,
            role=role,
            status=UserStatus.PENDING,
        )

    def mark_otp_dispatched(self) -> None:
        self.otp_dispatched_at = datetime.now(timezone.utc)

    def reinvite(self, name: str, telephone: str, role: "UserRole") -> None:
        if self.status != UserStatus.INACTIVE:
            raise ValueError(f"Can only re-invite an inactive user, current status: '{self.status.value}'")
        self.name              = name
        self.telephone         = telephone
        self.role              = role
        self.status            = UserStatus.PENDING
        self.created_at        = datetime.now(timezone.utc)
        self.otp_dispatched_at = None
        self.otp_verified_at   = None
        self.activated_at      = None

    def verify_otp(self) -> None:
        if self.status != UserStatus.PENDING:
            raise ValueError(f"OTP can only be verified for a pending user, current status: '{self.status.value}'")
        self.status          = UserStatus.PENDING_APPROVAL
        self.otp_verified_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        if self.status != UserStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot activate user with status '{self.status.value}' — OTP must be verified first")
        self.status       = UserStatus.ACTIVE
        self.activated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        if self.status not in (UserStatus.PENDING, UserStatus.PENDING_APPROVAL):
            raise ValueError(f"Cannot cancel invitation with status '{self.status.value}'")
        self.status = UserStatus.INACTIVE
