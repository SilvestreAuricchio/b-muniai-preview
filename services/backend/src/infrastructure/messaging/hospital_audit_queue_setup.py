AUDIT_QUEUE = "hospital.audit"


def declare_audit_queue(channel) -> None:
    """Idempotent — safe to call on every connection."""
    channel.queue_declare(queue=AUDIT_QUEUE, durable=True)
