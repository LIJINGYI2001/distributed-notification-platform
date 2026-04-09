import json
import time
from pathlib import Path
import sys

import pika
import random

# 让 worker 可以导入 code/shared 里的文件
# current path -→ absolute path -→ back 2 layer: to /code
BASE_DIR = Path(__file__).resolve().parents[2]
# put in Python search module
sys.path.append(str(BASE_DIR))

from shared.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    TIMEOUT_SECONDS, # Timeout Fail
    RETRY_BACKOFF_SECONDS,
    DEAD_LETTER_QUEUE,
)
from shared.logger import log_event



SERVICE_NAME = "email-worker-1"
QUEUE_NAME = "email_normal_queue"

def process_message(body: bytes):
    # RabbitMQ message (bytes type)
    # bytes -→ JSON -→ dict (producer: body=json.dumps(message).encode("utf-8"))
    message = json.loads(body.decode("utf-8"))

    # read or set null (message["xx"] will error when null)
    request_id = message.get("request_id", "") 
    notification_id = message.get("notification_id", "")
    trace_id = message.get("trace_id", "")
    channel = message.get("channel", "")
    priority = message.get("priority", "")
    #read fail properties
    force_fail = message.get("force_fail")
    force_timeout = message.get("force_timeout")

    # record current time (secend) -→ for calculate total time cost
    start_time = time.time()

    #log processing, print
    log_event(
        service_name=SERVICE_NAME,
        level="INFO",
        event="notification_processing",
        status="processing",
        request_id=request_id,
        notification_id=notification_id,
        trace_id=trace_id,
        channel=channel,
        priority=priority,
        latency_ms=0,
    )

    # Fail scenarios simulation
    # random_fail = random.random() < 0.3
    # if random_fail:
    #     raise RuntimeError("Random Simulated delivery failure")
    if force_fail:
        raise RuntimeError("Simulated delivery failure")
    if force_timeout:
        time.sleep(TIMEOUT_SECONDS+1)
        raise TimeoutError("Simulated timeout: processing exceeded 5 seconds")
    
    # Normal scenario
    # 模拟发送耗时
    time.sleep(1)

    # calculate cost time
    latency_ms = int((time.time() - start_time) * 1000) # ms

    #log delivered, print
    log_event(
        service_name=SERVICE_NAME,
        level="INFO",
        event="notification_delivered",
        status="delivered",
        request_id=request_id,
        notification_id=notification_id,
        trace_id=trace_id,
        channel=channel,
        priority=priority,
        latency_ms=latency_ms, # 1000-
    )

# AutoCall (such as process_message) once RabbitMQ send message
# channel(ack,nack);method(delivery_tag);properties(headers, durable,xx);body 
def callback(ch, method, properties, body):
    # Fail properties for push. Reread to prevent the fail of process_message()
    message = json.loads(body.decode("utf-8"))

    request_id = message.get("request_id", "")
    notification_id = message.get("notification_id", "")
    trace_id = message.get("trace_id", "")
    channel = message.get("channel", "")
    priority = message.get("priority", "")

    retry_count = message.get("retry_count", 0)
    max_retries = message.get("max_retries", 3)

    try:
        process_message(body)
        # send to RabbitMQ, delete it from queue
        ch.basic_ack(delivery_tag=method.delivery_tag) # acknowledgement

    except Exception as e:
        log_event(
            service_name=SERVICE_NAME,
            level="ERROR",
            event="notification_failed",
            status="failed",
            request_id=request_id,
            notification_id=notification_id,
            trace_id=trace_id,
            channel=channel,
            priority=priority,
            latency_ms=0,
        )
        print(f"[{SERVICE_NAME}] error: {e}")

        if retry_count < max_retries:
            message["retry_count"] = retry_count + 1
            message["status"] = "retrying"
            # process fail
            log_event(
                service_name=SERVICE_NAME,
                level="WARNING",
                event="notification_retrying",
                status="retrying",
                request_id=request_id,
                notification_id=notification_id,
                trace_id=trace_id,
                channel=channel,
                priority=priority,
                latency_ms=0,
            )
            time.sleep(RETRY_BACKOFF_SECONDS)
            publish_message(ch, QUEUE_NAME, message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            message["status"] = "dead_letter"
            log_event(
                service_name=SERVICE_NAME,
                level="ERROR",
                event="notification_dead_letter",
                status="dead_letter",
                request_id=request_id,
                notification_id=notification_id,
                trace_id=trace_id,
                channel=channel,
                priority=priority,
                latency_ms=0,
            )

            publish_message(ch, DEAD_LETTER_QUEUE, message)
            # ensure fail
            ch.basic_ack(delivery_tag=method.delivery_tag) # no acknowledgement

# Fail: retry_publish
def publish_message(channel, queue_name, message: dict):
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(
            delivery_mode=2
        ),
    )

def main():
    # Set parameter
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )

    # Connection
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    # create if not existing: durable
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    print(f"[{SERVICE_NAME}] waiting for messages from {QUEUE_NAME}...")

    # setup rule: if this queue come : processing in callback
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
    )
    # supervise channel
    channel.start_consuming()

# if run directly, run main()
if __name__ == "__main__":
    main()