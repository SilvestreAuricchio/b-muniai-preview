import json
import logging

import pika

from src.application.ports.audit_publisher_port import AuditPublisherPort
from src.infrastructure.messaging.hospital_audit_queue_setup import declare_audit_queue, AUDIT_QUEUE

_log = logging.getLogger(__name__)


class HospitalAuditPublisher(AuditPublisherPort):
    def __init__(self, amqp_url: str) -> None:
        self._amqp_url = amqp_url

    def publish_hospital_change(self, payload: dict) -> None:
        try:
            conn = pika.BlockingConnection(pika.URLParameters(self._amqp_url))
            try:
                ch = conn.channel()
                declare_audit_queue(ch)
                ch.basic_publish(
                    exchange="",
                    routing_key=AUDIT_QUEUE,
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
            finally:
                conn.close()
            _log.info(
                "HOSPITAL_AUDIT published action=%s hospitalId=%s",
                payload.get("action"),
                payload.get("hospitalId"),
            )
        except Exception as exc:
            _log.error(
                "Failed to publish hospital audit action=%s hospitalId=%s: %s",
                payload.get("action"),
                payload.get("hospitalId"),
                exc,
            )
