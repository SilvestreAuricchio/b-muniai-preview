"""
OTP Dispatcher Consumer
=======================
Subscribes to the `otp.challenge` RabbitMQ queue and delivers the OTP via
every configured channel (email, WhatsApp, SMS).

Retry semantics:
  - ALL channels are attempted regardless of individual failures.
  - If every channel succeeds  → basic_ack   (message removed from queue)
  - If any channel fails       → basic_nack  requeue=True  (message requeued
    for the next available consumer; the broker will redeliver it)

Run:
  python -m src.infrastructure.messaging.otp_dispatcher_consumer
"""
import json
import logging
import os
import time

import pika

from src.application.ports.otp_sender_port import OTPSenderPort
from src.infrastructure.messaging.noop_otp_sender import (
    NoOpEmailSender,
    NoOpWhatsAppSender,
    NoOpSMSSender,
)

_log = logging.getLogger(__name__)

QUEUE = "otp.challenge"


def _build_senders() -> list[OTPSenderPort]:
    # Swap NoOp senders for real adapters (SendGrid, Twilio, …) here.
    return [NoOpEmailSender(), NoOpWhatsAppSender(), NoOpSMSSender()]


def _on_message(
    channel: pika.channel.Channel,
    method: pika.spec.Basic.Deliver,
    _props: pika.spec.BasicProperties,
    body: bytes,
    senders: list[OTPSenderPort],
) -> None:
    try:
        payload = json.loads(body)
        uuid        = payload["uuid"]
        email       = payload["email"]
        telephone   = payload["telephone"]
        otp         = payload["otp"]
        ttl_seconds = payload["ttl_seconds"]
    except (json.JSONDecodeError, KeyError) as exc:
        _log.error("Malformed OTP message — discarding: %s", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    _log.info("Dispatching OTP uuid=%s via %d channel(s)", uuid, len(senders))

    failures: list[str] = []
    for sender in senders:
        try:
            sender.send(email, telephone, otp, ttl_seconds)
        except Exception as exc:
            name = type(sender).__name__
            _log.error("Channel %s failed for uuid=%s: %s", name, uuid, exc)
            failures.append(name)

    if failures:
        _log.warning("uuid=%s — %d channel(s) failed %s → NACK requeue", uuid, len(failures), failures)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    else:
        _log.info("uuid=%s — all channels delivered → ACK", uuid)
        channel.basic_ack(delivery_tag=method.delivery_tag)


def run(amqp_url: str) -> None:
    senders = _build_senders()

    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
            ch = connection.channel()
            ch.queue_declare(queue=QUEUE, durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(
                queue=QUEUE,
                on_message_callback=lambda c, m, p, b: _on_message(c, m, p, b, senders),
            )
            _log.info("OTP dispatcher ready — consuming queue=%s", QUEUE)
            ch.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            _log.error("RabbitMQ connection lost: %s — retrying in 5s", exc)
            time.sleep(5)
        except KeyboardInterrupt:
            _log.info("OTP dispatcher stopped")
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    run(url)
