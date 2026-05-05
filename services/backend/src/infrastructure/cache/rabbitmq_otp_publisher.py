"""
Production ChallengePort implementation.

Dispatch path
─────────────
  issue()   1. Store {otp, psa_uuid} in Redis with TTL  (so verify/revoke work
               immediately, independently of the async consumer)
            2. Publish OTP_CHALLENGE message to RabbitMQ queue `otp.challenge`

  consumer  Reads the queue, sends OTP via email + WhatsApp + SMS.
            ACK on all-success; NACK+requeue on any failure → automatic retry.
            See: src/infrastructure/messaging/otp_dispatcher_consumer.py

  verify()  Reads directly from Redis — no queue round-trip.
  revoke()  Deletes from Redis — no queue round-trip.

A new pika BlockingConnection is opened per issue() call so this adapter is
safe under multi-threaded Flask/Gunicorn workers.
"""
import json
import time
import logging

import redis
import pika

from src.application.ports.challenge_port import ChallengePort

_log = logging.getLogger(__name__)

_QUEUE   = "otp.challenge"
_KEY_TPL = "otp:{uuid}"


class RabbitMQOTPPublisher(ChallengePort):
    def __init__(self, amqp_url: str, redis_url: str) -> None:
        self._amqp_url = amqp_url
        self._redis    = redis.from_url(redis_url, decode_responses=True)

    # ── ChallengePort ──────────────────────────────────────────────────────

    def issue(self, uuid: str, email: str, telephone: str, otp: str, psa_uuid: str, ttl_seconds: int) -> None:
        # 1. Persist in Redis so verify() works before the consumer runs
        key = _KEY_TPL.format(uuid=uuid)
        self._redis.hset(key, mapping={"otp": otp, "psa_uuid": psa_uuid})
        self._redis.expire(key, ttl_seconds)

        # 2. Publish dispatch event — consumer handles multi-channel delivery
        payload = json.dumps({
            "uuid":        uuid,
            "email":       email,
            "telephone":   telephone,
            "otp":         otp,
            "ttl_seconds": ttl_seconds,
        })
        conn = pika.BlockingConnection(pika.URLParameters(self._amqp_url))
        try:
            ch = conn.channel()
            ch.queue_declare(queue=_QUEUE, durable=True)
            ch.basic_publish(
                exchange="",
                routing_key=_QUEUE,
                body=payload,
                properties=pika.BasicProperties(delivery_mode=2),  # persistent
            )
        finally:
            conn.close()

        _log.info("OTP_CHALLENGE published uuid=%s → queue=%s", uuid, _QUEUE)

    def verify(self, uuid: str, otp: str) -> str | None:
        entry = self._redis.hgetall(_KEY_TPL.format(uuid=uuid))
        if not entry:
            return None
        if entry.get("otp") != otp:
            return None
        return entry.get("psa_uuid")

    def revoke(self, uuid: str) -> None:
        self._redis.delete(_KEY_TPL.format(uuid=uuid))
        _log.info("OTP revoked uuid=%s", uuid)
