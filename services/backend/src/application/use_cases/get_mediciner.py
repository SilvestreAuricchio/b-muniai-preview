from src.application.ports.user_repository import UserRepository
from src.application.ports.mediciner_repository import MedicineerRepository
from src.domain.entities.user import User
from src.domain.entities.mediciner import MedicineerProfile


class GetMedicineerUseCase:
    def __init__(self, user_repo: UserRepository, mediciner_repo: MedicineerRepository) -> None:
        self._user_repo     = user_repo
        self._mediciner_repo = mediciner_repo

    def execute(self, user_uuid: str) -> tuple[User, MedicineerProfile]:
        user = self._user_repo.find_by_uuid(user_uuid)
        if not user:
            raise LookupError(f"Mediciner not found: {user_uuid}")
        profile = self._mediciner_repo.find_profile_by_user_uuid(user_uuid)
        if not profile:
            raise LookupError(f"Mediciner profile not found: {user_uuid}")
        return user, profile
