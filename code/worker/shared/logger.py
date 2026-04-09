import json
from datetime import datetime, timezone


def now_utc():
    # return current time string in UTC TimeZone
    # 4Year-month-dayT(seperate)hour:min:s Z(UTC): 2026-03-26T03:16:45Z
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Dict definition
def log_event(
    service_name,
    level,
    event,
    status,
    request_id="",
    notification_id="",
    trace_id="",
    channel="",
    priority="",
    latency_ms=0,
):
    log_data = {
        "timestamp": now_utc(),
        "service_name": service_name,
        "level": level,
        "request_id": request_id,
        "notification_id": notification_id,
        "trace_id": trace_id,
        "event": event,
        "channel": channel,
        "priority": priority,
        "status": status,
        "latency_ms": latency_ms,
    }
    # From dict to JSON format, prevent chinese characters
    print(json.dumps(log_data, ensure_ascii=False))