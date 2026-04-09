from fastapi import FastAPI
from datetime import datetime, timezone
import pika

from pathlib import Path
import sys
# 让 monitoring 可以导入 shared 里的文件
# current path -→ absolute path -→ back 1 layer: to /code
BASE_DIR = Path(__file__).resolve().parents[1]
# put in Python search module
sys.path.append(str(BASE_DIR))
from shared.metrics_store import load_metrics, reset_metrics
from shared.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
)

app = FastAPI()

def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def check_metrics_ok():
    try:
        metrics = load_metrics()
        required_keys = [
            "notifications_processing_attempts_total",
            "notifications_delivered_total",
            "delivery_latency_ms_total",
            "notifications_failed_total",
            "notifications_retried_total",
            "dead_letter_total",
        ]
        for key in required_keys:
            if key not in metrics:
                return False, f"missing metrics key: {key}"
        return True, "metrics file readable"
    except Exception as e:
        return False, f"metrics error: {e}"

def check_rabbitmq_ok():
    connection = None
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            blocked_connection_timeout=3,
            socket_timeout=3,
        )
        connection = pika.BlockingConnection(parameters)
        return True, "rabbitmq reachable"
    except Exception as e:
        return False, f"rabbitmq error: {e}"
    finally:
        if connection and connection.is_open:
            connection.close()

@app.get("/health")
def health():
    metrics_ok, metrics_msg = check_metrics_ok()
    rabbit_ok, rabbit_msg = check_rabbitmq_ok()

    # status setting
    # default status: UP
    status = "UP"
    # exist one unnormal -→ degrade
    if not metrics_ok or not rabbit_ok:
        status = "DEGRADED"

    # load form documentation
    metrics = load_metrics()

    return {
        "service_name": "monitoring",
        "status": status,
        "timestamp": now_utc(),
        "checks": {
            "metrics_store": {
                "ok": metrics_ok,
                "message": metrics_msg,
            },
            "rabbitmq": {
                "ok": rabbit_ok,
                "message": rabbit_msg,
            },
        },
        "summary": {
            "notifications_processing_attempts_total": metrics.get("notifications_processing_attempts_total", 0),
            "dead_letter_total": metrics.get("dead_letter_total", 0),
        },
    }

@app.get("/metrics")
def get_metrics():
    # load form documentation
    metrics = load_metrics()

    processed = metrics["notifications_processing_attempts_total"]
    delivered = metrics["notifications_delivered_total"]
    failed = metrics["notifications_failed_total"]

    # avg_latency
    avg_latency = 0
    if delivered > 0:
        avg_latency = metrics["delivery_latency_ms_total"] / delivered

    # success_rate & failure_rate
    success_rate = 0
    failure_rate = 0
    if processed > 0:
        success_rate = delivered / processed
        failure_rate = failed / processed

    # throughput
    start_time_str = metrics.get("metrics_start_time")
    throughput = 0
    if start_time_str:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
        if elapsed_seconds > 0:
            throughput = processed / elapsed_seconds

    return {
        **metrics,
        "delivery_latency_ms_avg": avg_latency,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "throughput_msgs_per_sec": throughput,
    }

@app.get("/metrics/reset")
def reset_metrics_api():
    reset_metrics()
    return {"success": True, "message": "metrics reset"}