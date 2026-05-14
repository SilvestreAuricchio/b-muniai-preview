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

from src.application.ports.otp_sender_port import OTPSenderPort, PermanentDeliveryError
from src.infrastructure.messaging.noop_otp_sender import (
    NoOpEmailSender,
    NoOpWhatsAppSender,
    NoOpSMSSender,
)
from src.infrastructure.messaging.smtp_otp_sender import SmtpOTPSender
from src.infrastructure.messaging.otp_queue_setup import declare_otp_queues, MAIN_QUEUE, FAILED_QUEUE

_log = logging.getLogger(__name__)


def _build_email_sender() -> OTPSenderPort:
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        _log.warning("SMTP_HOST not set — email OTP will not be delivered (NoOp)")
        return NoOpEmailSender()
    return SmtpOTPSender(
        host=host,
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ.get("SMTP_USER", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        from_addr=os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
    )


def _build_senders() -> list[OTPSenderPort]:
    return [
        _build_email_sender(),
        NoOpWhatsAppSender(),   # replace with Twilio/360dialog adapter
        NoOpSMSSender(),        # replace with Twilio adapter
    ]


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

    base_url = payload.get("base_url", "")
    _log.info("Dispatching OTP uuid=%s via %d channel(s) base_url=%r", uuid, len(senders), base_url)

    transient_failures: list[str] = []
    permanent_failures: list[str] = []

    for sender in senders:
        name = type(sender).__name__
        try:
            sender.send(uuid, email, telephone, otp, ttl_seconds, base_url)
        except PermanentDeliveryError as exc:
            _log.error("Channel %s permanent failure uuid=%s: %s", name, uuid, exc)
            permanent_failures.append(name)
        except Exception as exc:
            _log.error("Channel %s transient failure uuid=%s: %s", name, uuid, exc)
            transient_failures.append(name)

    if transient_failures:
        _log.warning("uuid=%s — transient failures %s → NACK requeue", uuid, transient_failures)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    elif permanent_failures:
        _log.error(
            "uuid=%s — permanent failures %s → NACK → routed to DLQ '%s' (inspect via /rabbitmq)",
            uuid, permanent_failures, FAILED_QUEUE,
        )
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        _log.info("uuid=%s — all channels delivered → ACK", uuid)
        channel.basic_ack(delivery_tag=method.delivery_tag)


def run(amqp_url: str) -> None:
    senders = _build_senders()

    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
            ch = connection.channel()
            declare_otp_queues(ch)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(
                queue=MAIN_QUEUE,
                on_message_callback=lambda c, m, p, b: _on_message(c, m, p, b, senders),
            )
            _log.info("OTP dispatcher ready — queue=%s  DLQ=%s", MAIN_QUEUE, FAILED_QUEUE)
            ch.start_consuming()
        except (pika.exceptions.AMQPConnectionError, OSError) as exc:
            _log.error("RabbitMQ connection error: %s — retrying in 5s", exc)
            time.sleep(5)
        except KeyboardInterrupt:
            _log.info("OTP dispatcher stopped")
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    run(url)
