import json
import logging
from typing import Any
import pika
from src.application.ports.log_port import LogPort

_log = logging.getLogger(__name__)


class RabbitMQLogAdapter(LogPort):
    QUEUE = "log_events"

    def __init__(self, url: str) -> None:
        self._url = url

    def publish(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        performed_by: str,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> None:
        body = json.dumps({
            "action": action,
            "entityType": entity_type,
            "entityId": entity_id,
            "performedBy": performed_by,
            "payload": payload,
            "correlationId": correlation_id,
        })
        try:
            params = pika.URLParameters(self._url)
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            ch.queue_declare(queue=self.QUEUE, durable=True)
            ch.basic_publish(
                exchange="",
                routing_key=self.QUEUE,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            conn.close()
        except Exception:
            _log.exception("Failed to publish LOG_EVENT — action=%s correlationId=%s", action, correlation_id)
            raise
