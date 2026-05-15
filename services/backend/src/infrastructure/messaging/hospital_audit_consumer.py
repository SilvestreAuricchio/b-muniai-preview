"""
Hospital Audit Consumer
=======================
Subscribes to the `hospital.audit` RabbitMQ queue and writes each event
as a document to the MongoDB `hospital_audit_log` collection.

Retry semantics:
  - Transient errors (MongoDB connection loss, etc.) → NACK requeue=True
  - Permanent errors (bad JSON, missing required fields) → NACK requeue=False

Run:
  python -m src.infrastructure.messaging.hospital_audit_consumer
"""
import json
import logging
import os
import time

import pika
import pymongo

from src.infrastructure.messaging.hospital_audit_queue_setup import declare_audit_queue, AUDIT_QUEUE

_log = logging.getLogger(__name__)

REQUIRED_FIELDS = {"action", "hospitalId", "userId", "timestamp"}


def _ensure_indexes(collection) -> None:
    collection.create_index([("hospitalId", pymongo.ASCENDING)], unique=False)
    collection.create_index([("userId", pymongo.ASCENDING)], unique=False)
    collection.create_index([("timestamp", pymongo.DESCENDING)], unique=False)
    _log.info("hospital_audit_log indexes ensured")


def _on_message(
    channel: pika.channel.Channel,
    method: pika.spec.Basic.Deliver,
    _props: pika.spec.BasicProperties,
    body: bytes,
    collection,
) -> None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        _log.error("Malformed audit message (bad JSON) — discarding: %s", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        _log.error("Audit message missing fields %s — discarding", missing)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    try:
        collection.insert_one(payload)
        _log.info(
            "Audit document inserted action=%s hospitalId=%s",
            payload.get("action"),
            payload.get("hospitalId"),
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        _log.error(
            "Transient error inserting audit document hospitalId=%s: %s — requeueing",
            payload.get("hospitalId"),
            exc,
        )
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def run(amqp_url: str, mongodb_url: str) -> None:
    mongo_client = pymongo.MongoClient(mongodb_url)
    db_name = pymongo.uri_parser.parse_uri(mongodb_url).get("database") or "muniai"
    collection = mongo_client[db_name]["hospital_audit_log"]
    _ensure_indexes(collection)

    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
            ch = connection.channel()
            declare_audit_queue(ch)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(
                queue=AUDIT_QUEUE,
                on_message_callback=lambda c, m, p, b: _on_message(c, m, p, b, collection),
            )
            _log.info("Hospital audit consumer ready — queue=%s", AUDIT_QUEUE)
            ch.start_consuming()
        except (pika.exceptions.AMQPConnectionError, OSError) as exc:
            _log.error("RabbitMQ connection error: %s — retrying in 5s", exc)
            time.sleep(5)
        except KeyboardInterrupt:
            _log.info("Hospital audit consumer stopped")
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    amqp_url   = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/muniai")
    run(amqp_url, mongodb_url)
