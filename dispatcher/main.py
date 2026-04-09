import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Dict, Any

import pika
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn


# =========================
# Configuration
# =========================
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

DISPATCHER_HOST = os.getenv("DISPATCHER_HOST", "0.0.0.0")
DISPATCHER_PORT = int(os.getenv("DISPATCHER_PORT", "8001"))

INCOMING_QUEUE = "incoming_queue"
DEAD_LETTER_QUEUE = "dead_letter_queue"

QUEUE_MAP = {
    ("email", "high"): "email_high_queue",
    ("email", "normal"): "email_normal_queue",
    ("push", "high"): "push_high_queue",
    ("push", "normal"): "push_normal_queue",
    ("inapp", "high"): "inapp_high_queue",
    ("inapp", "normal"): "inapp_normal_queue",
}

VALID_CHANNELS = {"email", "push", "inapp"}
VALID_PRIORITIES = {"high", "normal"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# =========================
# Logging
# =========================
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("dispatcher")


# =========================
# Metrics / Health State
# =========================
state = {
    "service_name": "dispatcher",
    "status": "STARTING",
    "rabbitmq_connected": False,
    "consumer_running": False,
    "start_time": time.time(),
}

metrics = {
    "notifications_received_total": 0,
    "notifications_dispatched_total": 0,
    "notifications_failed_total": 0,
    "invalid_messages_total": 0,
    "dead_letter_total": 0,
}

shutdown_event = threading.Event()


# =========================
# FastAPI App
# =========================
app = FastAPI(title="Dispatcher Service", version="1.0.0")


@app.get("/health")
def health():
    overall_status = "UP" if state["rabbitmq_connected"] and state["consumer_running"] else "DEGRADED"
    return JSONResponse(
        {
            "service_name": state["service_name"],
            "status": overall_status,
            "dependencies": {
                "rabbitmq": "UP" if state["rabbitmq_connected"] else "DOWN"
            },
            "consumer_running": state["consumer_running"],
            "uptime_seconds": round(time.time() - state["start_time"], 2),
        }
    )


@app.get("/metrics")
def get_metrics():
    return JSONResponse(metrics)


# =========================
# RabbitMQ Utilities
# =========================
def build_connection() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
    )
    return pika.BlockingConnection(parameters)


def declare_queues(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    all_queues = [INCOMING_QUEUE, DEAD_LETTER_QUEUE] + list(QUEUE_MAP.values())
    for queue_name in all_queues:
        channel.queue_declare(queue=queue_name, durable=True)
    logger.info("All dispatcher queues declared successfully.")


def validate_message(message: Dict[str, Any]) -> bool:
    channel = message.get("channel")
    priority = message.get("priority")

    if channel not in VALID_CHANNELS:
        return False
    if priority not in VALID_PRIORITIES:
        return False
    return True


def resolve_target_queue(message: Dict[str, Any]) -> str:
    return QUEUE_MAP[(message["channel"], message["priority"])]


def publish_message(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    queue_name: str,
    message: Dict[str, Any],
) -> None:
    body = json.dumps(message)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=body,
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )


def move_to_dead_letter(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    message: Dict[str, Any],
    error_code: str,
    error_message: str,
) -> None:
    message["status"] = "dead_letter"
    message["error_code"] = error_code
    message["error_message"] = error_message
    message["source"] = "dispatcher"

    publish_message(channel, DEAD_LETTER_QUEUE, message)
    metrics["dead_letter_total"] += 1


# =========================
# Consumer Logic
# =========================
def on_message(ch, method, properties, body):
    metrics["notifications_received_total"] += 1

    try:
        raw_message = body.decode("utf-8")
        message = json.loads(raw_message)

        notification_id = message.get("notification_id", "unknown")
        request_id = message.get("request_id", "unknown")
        channel_name = message.get("channel")
        priority = message.get("priority")

        logger.info(
            json.dumps(
                {
                    "service_name": "dispatcher",
                    "event": "message_received",
                    "notification_id": notification_id,
                    "request_id": request_id,
                    "channel": channel_name,
                    "priority": priority,
                    "status": "received",
                }
            )
        )

        if not validate_message(message):
            metrics["invalid_messages_total"] += 1
            metrics["notifications_failed_total"] += 1

            logger.error(
                json.dumps(
                    {
                        "service_name": "dispatcher",
                        "event": "invalid_message",
                        "notification_id": notification_id,
                        "request_id": request_id,
                        "status": "failed",
                        "error_code": "INVALID_INPUT",
                    }
                )
            )

            move_to_dead_letter(
                ch,
                message,
                error_code="INVALID_INPUT",
                error_message="channel or priority is invalid",
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        target_queue = resolve_target_queue(message)
        message["status"] = "dispatched"
        message["source"] = "dispatcher"

        publish_message(ch, target_queue, message)
        metrics["notifications_dispatched_total"] += 1

        logger.info(
            json.dumps(
                {
                    "service_name": "dispatcher",
                    "event": "message_dispatched",
                    "notification_id": notification_id,
                    "request_id": request_id,
                    "target_queue": target_queue,
                    "channel": channel_name,
                    "priority": priority,
                    "status": "dispatched",
                }
            )
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError:
        metrics["notifications_failed_total"] += 1
        metrics["invalid_messages_total"] += 1
        logger.exception("Invalid JSON received. Dropping message to dead letter queue.")
        fallback_message = {
            "status": "dead_letter",
            "source": "dispatcher",
            "error_code": "INVALID_JSON",
            "error_message": "message body is not valid JSON",
        }
        move_to_dead_letter(
            ch,
            fallback_message,
            error_code="INVALID_JSON",
            error_message="message body is not valid JSON",
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        metrics["notifications_failed_total"] += 1
        logger.exception(f"Unexpected dispatcher error: {e}")
        # 不 ack，让 RabbitMQ 重新投递
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_consumer():
    while not shutdown_event.is_set():
        connection = None
        try:
            logger.info("Connecting to RabbitMQ...")
            connection = build_connection()
            channel = connection.channel()
            declare_queues(channel)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=INCOMING_QUEUE, on_message_callback=on_message)

            state["rabbitmq_connected"] = True
            state["consumer_running"] = True
            state["status"] = "UP"

            logger.info("Dispatcher consumer started. Waiting for messages...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            state["rabbitmq_connected"] = False
            state["consumer_running"] = False
            state["status"] = "DEGRADED"
            logger.warning("RabbitMQ connection failed. Retrying in 5 seconds...")
            time.sleep(5)

        except Exception as e:
            state["consumer_running"] = False
            state["status"] = "DEGRADED"
            logger.exception(f"Dispatcher crashed unexpectedly: {e}")
            time.sleep(5)

        finally:
            if connection and connection.is_open:
                connection.close()


# =========================
# Graceful Shutdown
# =========================
def handle_shutdown(signum, frame):
    logger.info(f"Received shutdown signal: {signum}")
    shutdown_event.set()
    state["consumer_running"] = False
    state["status"] = "DOWN"
    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# =========================
# Main Entry
# =========================
def run_api():
    uvicorn.run(app, host=DISPATCHER_HOST, port=DISPATCHER_PORT)


if __name__ == "__main__":
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
    run_api()