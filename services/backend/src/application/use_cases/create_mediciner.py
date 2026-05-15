from dataclasses import dataclass

from src.domain.entities.user import UserRole
from src.domain.entities.hospital import UserHospital
from src.domain.entities.mediciner import MedicineerProfile
from src.domain.validation.tax_id import validate_tax_id
from src.application.ports.mediciner_repository import MedicineerRepository
from src.application.ports.hospital_repository import HospitalRepository
from src.application.ports.log_port import LogPort
from src.application.use_cases.create_user import CreateUserUseCase, CreateUserCommand


@dataclass(frozen=True)
class CreateMedicineerCommand:
    name:         str
    email:        str
    telephone:    str
    cpf:          str
    performed_by: str
    correlation_id: str
    base_url:     str = ""
    specialty:    str = ""
    crm_state:    str = ""
    crm_number:   str = ""
    hospital_uuid: str = ""


class CreateMedicineerUseCase:
    def __init__(
        self,
        create_user_uc:  CreateUserUseCase,
        mediciner_repo:  MedicineerRepository,
        hospital_repo:   HospitalRepository,
        log:             LogPort,
    ) -> None:
        self._create_user   = create_user_uc
        self._mediciner_repo = mediciner_repo
        self._hospital_repo  = hospital_repo
        self._log            = log

    def execute(self, cmd: CreateMedicineerCommand):
        validate_tax_id("BR", cmd.cpf)

        result = self._create_user.execute(CreateUserCommand(
            name=cmd.name,
            telephone=cmd.telephone,
            email=cmd.email,
            role=UserRole.MEDICINER,
            performed_by=cmd.performed_by,
            correlation_id=cmd.correlation_id,
            base_url=cmd.base_url,
        ))

        user = result.user
        profile = MedicineerProfile(
            user_uuid=user.uuid,
            cpf=cmd.cpf.replace(".", "").replace("-", ""),
            email=cmd.email,
            specialty=cmd.specialty or None,
            crm_state=cmd.crm_state or None,
            crm_number=cmd.crm_number or None,
        )
        self._mediciner_repo.save_profile(profile)

        if cmd.hospital_uuid:
            self._hospital_repo.link_user(UserHospital(
                user_uuid=user.uuid,
                hospital_uuid=cmd.hospital_uuid,
                scope="Mediciner",
            ))
            self._log.publish(
                action="LINK_USER_HOSPITAL",
                entity_type="USER_HOSPITAL",
                entity_id=f"{user.uuid}:{cmd.hospital_uuid}",
                performed_by=cmd.performed_by,
                payload={"user_uuid": user.uuid, "hospital_uuid": cmd.hospital_uuid, "scope": "Mediciner"},
                correlation_id=cmd.correlation_id,
            )

        return result
