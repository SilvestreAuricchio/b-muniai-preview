"""
RabbitMQ topology for OTP challenge delivery.

        publish
  API ──────────► otp.challenge ──► otp-dispatcher consumer
                       │ NACK requeue=False (permanent failure)
                       ▼
                  otp.challenge.dlx  (direct exchange)
                       │
                       ▼
                  otp.challenge.failed  (DLQ — inspect via /rabbitmq management UI)

Messages in the DLQ carry x-death headers with original queue, reason, timestamp,
and retry count. They can be re-published manually or by a recovery script.
"""

MAIN_QUEUE   = "otp.challenge"
DLX_EXCHANGE = "otp.challenge.dlx"
FAILED_QUEUE = "otp.challenge.failed"


def declare_otp_queues(channel) -> None:
    """Idempotent — safe to call on every connection."""
    channel.exchange_declare(
        exchange=DLX_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )
    channel.queue_declare(
        queue=MAIN_QUEUE,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_EXCHANGE},
    )
    channel.queue_declare(queue=FAILED_QUEUE, durable=True)
    channel.queue_bind(
        queue=FAILED_QUEUE,
        exchange=DLX_EXCHANGE,
        routing_key=MAIN_QUEUE,
    )
