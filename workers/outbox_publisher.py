"""
Outbox Publisher Worker.

Bridges the outbox table and Kafka. Runs as a separate process,
independent of the FastAPI application.

Three-state polling loop:
1. Claim PENDING rows → mark PROCESSING (atomic, FOR UPDATE SKIP LOCKED)
2. Publish each row to Kafka
3. Mark each row SENT individually

Failure handling:
- Kafka publish fails: row stays PROCESSING, recovery job resets to PENDING
- Publisher crashes after claim: row stays PROCESSING, recovery job resets it
- Publisher crashes after publish but before SENT: duplicate publish on next
  run, downstream idempotency (processed_events table) handles it

Structured logging enables operational monitoring without metrics infrastructure:
- Log batch size, publish duration, failure counts per cycle
- A growing backlog of PENDING rows indicates publisher is unhealthy
"""

import asyncio
import json
import logging
import time

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.config import get_settings
from app.database import AsyncSessionFactory
from app.logging_config import setup_logging
from app.outbox.repository import claim_pending_events, mark_event_sent

settings = get_settings()
logger = logging.getLogger(__name__)


async def create_kafka_producer() -> AIOKafkaProducer:
    """
    Create and start an async Kafka producer.

    acks='all' — wait for all in-sync replicas to acknowledge.
    Strongest durability guarantee. Acceptable latency cost since
    we are already async and not in the request path.

    value_serializer — encodes string payload to bytes for Kafka.
    key_serializer — encodes transfer_id string to bytes.
    Used as Kafka partition key so the same transfer always
    routes to the same partition, preserving per-transfer ordering.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        acks="all",
        value_serializer=lambda v: v.encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await producer.start()
    logger.info("Kafka producer started bootstrap=%s", settings.kafka_bootstrap_servers)
    return producer


async def publish_batch(producer: AIOKafkaProducer) -> None:
    """
    One polling cycle:
    1. Open a DB session
    2. Claim a batch of PENDING events (FOR UPDATE SKIP LOCKED)
    3. For each event: publish to Kafka, then mark SENT
    4. Commit the session

    Each event is marked SENT individually — a failure on one row
    does not prevent others in the batch from being processed.
    """
    async with AsyncSessionFactory() as session:
        events = await claim_pending_events(
            session, batch_size=10
        )

        if not events:
            return

        start_time = time.monotonic()
        published = 0
        failed = 0

        for event in events:
            try:
                # Parse transfer_id from payload to use as Kafka partition key
                payload_data = json.loads(event.payload)
                transfer_id = payload_data["transfer_id"]

                await producer.send_and_wait(
                    topic=settings.kafka_transfer_topic,
                    value=event.payload,
                    key=transfer_id,
                )

                await mark_event_sent(session, event.id)
                published += 1

                logger.debug(
                    "Published outbox event id=%d transfer_id=%s",
                    event.id,
                    transfer_id,
                )

            except KafkaError as e:
                # Kafka publish failed — row stays PROCESSING
                # Recovery job will reset it to PENDING
                failed += 1
                logger.error(
                    "Failed to publish outbox event id=%d error=%s",
                    event.id,
                    str(e),
                )

        await session.commit()

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Structured log line for operational monitoring
        # Answers: is the publisher healthy? how fast is it processing?
        logger.info(
            "outbox.poll completed "
            "rows_fetched=%d rows_published=%d rows_failed=%d duration_ms=%d",
            len(events),
            published,
            failed,
            duration_ms,
        )


async def run_publisher() -> None:
    """
    Main publisher loop.

    Runs indefinitely, polling the outbox table every
    OUTBOX_POLL_INTERVAL_SECONDS seconds.

    Catches and logs all unexpected exceptions so a single bad cycle
    does not kill the publisher process — Docker will restart it
    on fatal errors via restart: on-failure.
    """
    logger.info(
        "Outbox publisher starting poll_interval=%ds",
        settings.outbox_poll_interval_seconds,
    )

    producer = await create_kafka_producer()

    try:
        while True:
            try:
                await publish_batch(producer)
            except Exception as e:
                # Unexpected error — log and continue to next cycle
                # Publisher stays alive, Docker restarts on fatal crash
                logger.exception("Unexpected error in publish_batch error=%s", str(e))

            await asyncio.sleep(settings.outbox_poll_interval_seconds)
    finally:
        # Always stop the producer cleanly on shutdown
        await producer.stop()
        logger.info("Kafka producer stopped")


if __name__ == "__main__":
    setup_logging(debug=settings.debug)
    asyncio.run(run_publisher())
