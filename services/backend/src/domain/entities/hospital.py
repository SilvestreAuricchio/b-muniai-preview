from dataclasses import dataclass
from enum import Enum
import uuid as _uuid


class SlotType(str, Enum):
    UTI = "UTI"
    PS  = "PS"
    PA  = "PA"
    CC  = "CC"
    ENF = "ENF"


@dataclass
class Hospital:
    uuid:       str           # surrogate PK
    cnpj:       str           # alternate key — 14 chars, no punctuation
    name:       str
    address:    str
    slot_types: list[SlotType]

    @staticmethod
    def create(cnpj: str, name: str, address: str, slot_types: list[str]) -> "Hospital":
        clean_cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
        parsed     = [SlotType(s) for s in slot_types]
        return Hospital(
            uuid=str(_uuid.uuid4()),
            cnpj=clean_cnpj,
            name=name,
            address=address,
            slot_types=parsed,
        )


@dataclass(frozen=True)
class UserHospital:
    user_uuid:     str
    hospital_uuid: str
    scope:         str   # "Scheduler" | "Mediciner"
