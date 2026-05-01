from dataclasses import dataclass
from src.domain.entities.user import User, UserRole
from src.application.ports.user_repository import UserRepository
from src.application.ports.log_port import LogPort


@dataclass(frozen=True)
class CreateUserCommand:
    name: str
    telephone: str
    email: str
    role: UserRole
    performed_by: str
    correlation_id: str


class CreateUserUseCase:
    def __init__(self, repo: UserRepository, log: LogPort) -> None:
        self._repo = repo
        self._log = log

    def execute(self, cmd: CreateUserCommand) -> User:
        if self._repo.find_by_email(cmd.email):
            raise ValueError(f"Email already registered: {cmd.email!r}")

        user = User.create(cmd.name, cmd.telephone, cmd.email, cmd.role)
        saved = self._repo.save(user)

        self._log.publish(
            action="CREATE_USER",
            entity_type="USER",
            entity_id=saved.uuid,
            performed_by=cmd.performed_by,
            payload={"name": cmd.name, "email": cmd.email, "role": cmd.role.value},
            correlation_id=cmd.correlation_id,
        )
        return saved
