import json
from pathlib import Path
from datetime import datetime, timezone
from filelock import FileLock

METRICS_FILE = Path(__file__).resolve().parents[1] / "monitoring" / "metrics.json"
# filelock for throughput calculate (prevent lost update)
LOCK_FILE = METRICS_FILE.with_suffix(".lock")

DEFAULT_METRICS = {
    # process
    # -→ [end:delivered] | [failed -→ (retry:↑ | end:dead)]

    # process & deliverd 
    "notifications_processing_attempts_total": 0,
    "notifications_delivered_total": 0,
    "delivery_latency_ms_total": 0,
    # failed
    "notifications_failed_total": 0,
    # retried
    "notifications_retried_total": 0,
    # dead_letter
    "dead_letter_total": 0,
    "metrics_start_time": None,
}

def load_metrics():
    if not METRICS_FILE.exists():
        reset_metrics()
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metrics(metrics):
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def reset_metrics():
    metrics = DEFAULT_METRICS.copy()
    metrics["metrics_start_time"] = now_utc()
    save_metrics(metrics)

# filelock: update_function as its paremeter
def update_metrics(update_fn):
    """
    auto update metrics:
    1. add lock
    2. read latest metrics
    3. invoking update_fn to update
    4. write back to doc
    5. automatical release lock
    """
    lock = FileLock(str(LOCK_FILE))

    with lock:
        metrics = load_metrics()
        update_fn(metrics)
        save_metrics(metrics)