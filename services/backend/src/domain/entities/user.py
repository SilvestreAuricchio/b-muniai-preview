from dataclasses import dataclass
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
    uuid: str
    name: str
    telephone: str
    email: str
    role: UserRole
    status: UserStatus

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

    def verify_otp(self) -> None:
        if self.status != UserStatus.PENDING:
            raise ValueError(f"OTP can only be verified for a pending user, current status: '{self.status.value}'")
        self.status = UserStatus.PENDING_APPROVAL

    def activate(self) -> None:
        if self.status != UserStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot activate user with status '{self.status.value}' — OTP must be verified first")
        self.status = UserStatus.ACTIVE

    def deactivate(self) -> None:
        if self.status not in (UserStatus.PENDING, UserStatus.PENDING_APPROVAL):
            raise ValueError(f"Cannot cancel invitation with status '{self.status.value}'")
        self.status = UserStatus.INACTIVE
