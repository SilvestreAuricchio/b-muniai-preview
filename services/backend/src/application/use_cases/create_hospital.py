from dataclasses import dataclass
from datetime import datetime, timezone
from src.domain.entities.hospital import Hospital
from src.application.ports.hospital_repository import HospitalRepository
from src.application.ports.log_port import LogPort
from src.application.ports.audit_publisher_port import AuditPublisherPort
from src.domain.validation.tax_id import validate_tax_id


@dataclass(frozen=True)
class CreateHospitalCommand:
    cnpj:           str
    name:           str
    address:        str
    slot_types:     list[str]
    performed_by:   str
    correlation_id: str
    country:        str = "BR"


@dataclass(frozen=True)
class CreateHospitalResult:
    hospital: Hospital


class CreateHospitalUseCase:
    def __init__(
        self,
        repo: HospitalRepository,
        log: LogPort,
        audit_publisher: AuditPublisherPort | None = None,
    ) -> None:
        self._repo            = repo
        self._log             = log
        self._audit_publisher = audit_publisher

    def execute(self, cmd: CreateHospitalCommand) -> CreateHospitalResult:
        clean_cnpj = cmd.cnpj.replace(".", "").replace("/", "").replace("-", "").strip().upper()
        validate_tax_id(cmd.country, clean_cnpj)
        if self._repo.find_by_cnpj(clean_cnpj):
            raise ValueError(f"CNPJ already registered: {clean_cnpj!r}")

        hospital = Hospital.create(cmd.cnpj, cmd.name, cmd.address, cmd.slot_types)
        saved    = self._repo.save(hospital)

        self._log.publish(
            action="CREATE_HOSPITAL",
            entity_type="HOSPITAL",
            entity_id=saved.uuid,
            performed_by=cmd.performed_by,
            payload={"name": cmd.name, "cnpj": saved.cnpj, "slot_types": cmd.slot_types},
            correlation_id=cmd.correlation_id,
        )

        if self._audit_publisher is not None:
            self._audit_publisher.publish_hospital_change({
                "action":     "CREATED",
                "hospitalId": saved.uuid,
                "userId":     cmd.performed_by,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "before":     None,
                "after": {
                    "uuid":       saved.uuid,
                    "cnpj":       saved.cnpj,
                    "name":       saved.name,
                    "address":    saved.address,
                    "slot_types": [s.value for s in saved.slot_types],
                },
            })

        return CreateHospitalResult(hospital=saved)
