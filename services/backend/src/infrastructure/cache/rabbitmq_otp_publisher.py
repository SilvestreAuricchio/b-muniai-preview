"""
Production ChallengePort implementation.

Dispatch path:
  issue()  → publishes OTP_CHALLENGE event to RabbitMQ
           → stores {otp, psa_uuid, expiry} in Redis (for verify/revoke)
  consumer → subscribes OTP_CHALLENGE queue
           → sends OTP via email + WhatsApp + SMS (all channels, fire-and-forget per channel)
           → channel failure does NOT fail the invitation flow

verify() and revoke() operate directly on Redis so they do not go through
the queue and remain synchronous.
"""
import json
import time
import logging
import redis
import pika

from src.application.ports.challenge_port import ChallengePort

_log = logging.getLogger(__name__)

_REDIS_KEY = "otp:{uuid}"


class RabbitMQOTPPublisher(ChallengePort):
    def __init__(self, amqp_url: str, redis_url: str, queue: str = "otp.challenge") -> None:
        self._queue      = queue
        self._redis      = redis.from_url(redis_url, decode_responses=True)
        self._connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
        self._channel    = self._connection.channel()
        self._channel.queue_declare(queue=queue, durable=True)

    def issue(self, uuid, email, telephone, otp, psa_uuid, ttl_seconds) -> None:
        expiry = time.time() + ttl_seconds
        # store for verify/revoke (Redis TTL matches challenge TTL)
        key = _REDIS_KEY.format(uuid=uuid)
        self._redis.hset(key, mapping={"otp": otp, "psa_uuid": psa_uuid})
        self._redis.expireat(key, int(expiry))

        # publish dispatch event — consumer sends email + WhatsApp + SMS
        payload = json.dumps({
            "uuid":        uuid,
            "email":       email,
            "telephone":   telephone,
            "otp":         otp,
            "ttl_seconds": ttl_seconds,
        })
        self._channel.basic_publish(
            exchange="",
            routing_key=self._queue,
            body=payload,
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        _log.info("OTP_CHALLENGE published uuid=%s → queue=%s", uuid, self._queue)

    def verify(self, uuid: str, otp: str) -> str | None:
        key = _REDIS_KEY.format(uuid=uuid)
        entry = self._redis.hgetall(key)
        if not entry:
            return None
        if entry.get("otp") != otp:
            return None
        return entry.get("psa_uuid")

    def revoke(self, uuid: str) -> None:
        self._redis.delete(_REDIS_KEY.format(uuid=uuid))
        _log.info("OTP_CHALLENGE revoked uuid=%s", uuid)
