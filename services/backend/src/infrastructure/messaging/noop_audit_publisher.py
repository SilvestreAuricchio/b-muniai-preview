from src.application.ports.audit_publisher_port import AuditPublisherPort


class NoOpAuditPublisher(AuditPublisherPort):
    def publish_hospital_change(self, payload: dict) -> None:
        pass
