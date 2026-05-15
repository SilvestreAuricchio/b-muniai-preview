from dataclasses import dataclass
from src.application.ports.mediciner_repository import MedicineerRepository
from src.domain.entities.mediciner import MedicineerProfile


@dataclass(frozen=True)
class UpdateMedicineerCommand:
    user_uuid:  str
    specialty:  str | None = None
    crm_state:  str | None = None
    crm_number: str | None = None


class UpdateMedicineerUseCase:
    def __init__(self, repo: MedicineerRepository) -> None:
        self._repo = repo

    def execute(self, cmd: UpdateMedicineerCommand) -> MedicineerProfile:
        profile = self._repo.find_profile_by_user_uuid(cmd.user_uuid)
        if not profile:
            raise LookupError(f"Mediciner profile not found: {cmd.user_uuid}")

        updated = MedicineerProfile(
            user_uuid=profile.user_uuid,
            cpf=profile.cpf,
            email=profile.email,
            specialty=cmd.specialty if cmd.specialty is not None else profile.specialty,
            crm_state=cmd.crm_state if cmd.crm_state is not None else profile.crm_state,
            crm_number=cmd.crm_number if cmd.crm_number is not None else profile.crm_number,
        )
        return self._repo.update_profile(updated)
