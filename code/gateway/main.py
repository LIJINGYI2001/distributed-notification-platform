from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import uuid
import time
import json
import pika

app = FastAPI()

# ===== 配置 =====
API_KEY = "team17-secret-key"
RATE_LIMIT_PER_MINUTE = 20

# RabbitMQ 配置
# 如果 RabbitMQ 和 dispatcher 在同一台电脑，本地测试就写 localhost
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_QUEUE = "incoming_queue"

# ===== 仅保留作查看用途，可删 =====
queue = []

# ===== rate limit =====
request_count = 0
start_time = time.time()

# ===== 请求结构 =====
class NotificationRequest(BaseModel):
    user_id: str
    channel: str
    priority: str
    title: str = ""
    message: str
    recipient: str

# ===== 工具函数 =====
def generate_id(prefix: str) -> str:
    now = datetime.utcnow().strftime("%Y%m%d")
    rand = str(uuid.uuid4())[:6]
    return f"{prefix}_{now}_{rand}"

def current_time() -> str:
    return datetime.utcnow().isoformat() + "Z"

def send_to_rabbitmq(message: dict) -> None:
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
        )
    )
    channel = connection.channel()

    # 声明队列，和 dispatcher 保持一致
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=RABBITMQ_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2  # persistent
        )
    )

    connection.close()

# ===== 健康检查 =====
@app.get("/health")
def health():
    return {
        "service_name": "gateway",
        "status": "UP",
        "timestamp": current_time()
    }

# ===== 主接口 =====
@app.post("/notifications")
async def create_notification(
    data: NotificationRequest,
    x_api_key: str = Header(...),
    x_request_id: str = Header(None)
):
    global request_count, start_time

    # ===== API KEY =====
    if x_api_key != API_KEY:
        return {
            "success": False,
            "error_code": "INVALID_API_KEY"
        }

    # ===== Rate Limit =====
    current = time.time()
    if current - start_time >= 60:
        request_count = 0
        start_time = current

    request_count += 1
    if request_count > RATE_LIMIT_PER_MINUTE:
        return {
            "success": False,
            "error_code": "RATE_LIMIT_EXCEEDED"
        }

    # ===== 校验 =====
    if data.channel not in ["email", "push", "inapp"]:
        return {"success": False, "error_code": "INVALID_CHANNEL"}

    if data.priority not in ["high", "normal"]:
        return {"success": False, "error_code": "INVALID_PRIORITY"}

    if not (1 <= len(data.message) <= 500):
        return {"success": False, "error_code": "INVALID_MESSAGE"}

    if not data.recipient:
        return {"success": False, "error_code": "INVALID_RECIPIENT"}

    # ===== 生成ID =====
    request_id = x_request_id or generate_id("req")
    notification_id = generate_id("noti")
    trace_id = generate_id("trace")

    # ===== 构建消息 =====
    message = {
        "notification_id": notification_id,
        "request_id": request_id,
        "user_id": data.user_id,
        "channel": data.channel,
        "priority": data.priority,
        "title": data.title,
        "message": data.message,
        "recipient": data.recipient,
        "status": "received",
        "retry_count": 0,
        "max_retries": 3,
        "created_at": current_time(),
        "trace_id": trace_id,
        "source": "gateway"
    }

    # ===== 发到 RabbitMQ，而不是本地列表 =====
    send_to_rabbitmq(message)

    # 可选：留一份本地查看
    queue.append(message)

    print({
        "service_name": "gateway",
        "event": "notification_queued",
        "notification_id": notification_id,
        "priority": data.priority,
        "channel": data.channel,
        "target_queue": "incoming_queue"
    })

    return {
        "success": True,
        "notification_id": notification_id,
        "request_id": request_id,
        "status": "accepted"
    }

# ===== 查看本地缓存（可选） =====
@app.get("/queue")
def get_queue():
    return JSONResponse(content=queue)