from dataclasses import dataclass
from datetime import datetime, timezone
from src.domain.entities.hospital import Hospital, SlotType
from src.application.ports.hospital_repository import HospitalRepository
from src.application.ports.log_port import LogPort
from src.application.ports.audit_publisher_port import AuditPublisherPort


@dataclass(frozen=True)
class UpdateHospitalCommand:
    uuid:           str
    name:           str
    address:        str
    slot_types:     list[str]
    performed_by:   str
    correlation_id: str


class UpdateHospitalUseCase:
    def __init__(
        self,
        repo: HospitalRepository,
        log: LogPort,
        audit_publisher: AuditPublisherPort | None = None,
    ) -> None:
        self._repo            = repo
        self._log             = log
        self._audit_publisher = audit_publisher

    def execute(self, cmd: UpdateHospitalCommand) -> Hospital:
        hospital = self._repo.find_by_uuid(cmd.uuid)
        if hospital is None:
            raise LookupError(f"Hospital not found: {cmd.uuid!r}")

        before_dict = {
            "uuid":       hospital.uuid,
            "cnpj":       hospital.cnpj,
            "name":       hospital.name,
            "address":    hospital.address,
            "slot_types": [s.value for s in hospital.slot_types],
        }

        hospital.name       = cmd.name
        hospital.address    = cmd.address
        hospital.slot_types = [SlotType(s) for s in cmd.slot_types]

        saved = self._repo.save(hospital)

        self._log.publish(
            action="UPDATE_HOSPITAL",
            entity_type="HOSPITAL",
            entity_id=cmd.uuid,
            performed_by=cmd.performed_by,
            payload={"name": cmd.name, "address": cmd.address, "slot_types": cmd.slot_types},
            correlation_id=cmd.correlation_id,
        )

        if self._audit_publisher is not None:
            self._audit_publisher.publish_hospital_change({
                "action":     "UPDATED",
                "hospitalId": saved.uuid,
                "userId":     cmd.performed_by,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "before":     before_dict,
                "after": {
                    "uuid":       saved.uuid,
                    "cnpj":       saved.cnpj,
                    "name":       saved.name,
                    "address":    saved.address,
                    "slot_types": [s.value for s in saved.slot_types],
                },
            })

        return saved
