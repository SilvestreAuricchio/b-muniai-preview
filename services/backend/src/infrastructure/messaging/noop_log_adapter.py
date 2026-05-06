import logging
from typing import Any
from src.application.ports.log_port import LogPort

_log = logging.getLogger(__name__)


class NoOpLogAdapter(LogPort):
    """Logs to stdout. Used when RabbitMQ is not configured."""

    def publish(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        performed_by: str,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> None:
        _log.info(
            "LOG_EVENT action=%s entity=%s/%s performedBy=%s correlationId=%s payload=%s",
            action, entity_type, entity_id, performed_by, correlation_id, payload,
        )
