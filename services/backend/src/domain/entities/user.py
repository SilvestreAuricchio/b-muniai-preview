from dataclasses import dataclass
from enum import Enum
import uuid as _uuid


class UserRole(str, Enum):
    SA_ROOT   = "SA-root"
    SCHEDULER = "Scheduler"
    MEDICINER = "Mediciner"


class UserStatus(str, Enum):
    PENDING  = "pending"
    ACTIVE   = "active"
    INACTIVE = "inactive"


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

    def activate(self) -> None:
        if self.status != UserStatus.PENDING:
            raise ValueError(f"Cannot activate user with status '{self.status.value}'")
        self.status = UserStatus.ACTIVE
