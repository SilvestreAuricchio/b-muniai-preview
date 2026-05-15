from dataclasses import dataclass


@dataclass
class MedicineerProfile:
    user_uuid:  str
    cpf:        str
    email:      str
    specialty:  str | None = None
    crm_state:  str | None = None
    crm_number: str | None = None
