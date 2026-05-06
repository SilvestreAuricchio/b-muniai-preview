from src.domain.entities.user import User
from src.application.ports.user_repository import UserRepository


class FindUserByEmailUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def execute(self, email: str) -> User | None:
        return self._repo.find_by_email(email)
