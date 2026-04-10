# Distributed Notification Routing System

## Dependencies

This project requires the following software:

* Python 3.10+
* RabbitMQ

Install required Python packages:

```bash
pip install fastapi uvicorn pika requests pydantic
```

---

## Start RabbitMQ

### Linux

```bash
sudo systemctl start rabbitmq-server
```

### macOS (Homebrew)

```bash
brew services start rabbitmq
```

### Windows (Docker recommended)

```bash
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

RabbitMQ Management Console:

```
http://localhost:15672
username: guest
password: guest
```

---

# Project Structure

```
project/

code/
    dispatcher/main.py
    gateway/simulator.py
    workers/inapp_worker/

serviceA/
    gateway/main.py

serviceB/
    workers/email_worker/
    workers/push_worker/
```

---

# Run Instructions

Start services **in the exact order below**

```
RabbitMQ → Dispatcher → Gateway → Workers → Simulator
```

---

## Step 1 — Start Dispatcher Service

Open terminal:

```bash
cd code/dispatcher
python main.py
```

Health check endpoint:

```
http://localhost:8001/health
```

Expected response:

```
status: UP
```

---

## Step 2 — Start Gateway Service

Open new terminal:

```bash
cd serviceA/gateway
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check endpoint:

```
http://localhost:8000/health
```

Expected response:

```
status: UP
```

---

## Step 3 — Start Worker Services

Open **three separate terminals**

### Email Worker

```bash
cd serviceB/workers/email_worker
python worker_1.py
```

### Push Worker

```bash
cd serviceB/workers/push_worker
python worker_1.py
```

### In-App Worker

```bash
cd code/workers/inapp_worker
python worker_1.py
```

Workers will begin listening to RabbitMQ priority queues automatically.

---

## Step 4 — Run Client Simulator

Open new terminal:

```bash
cd code/gateway
python simulator.py
```

The simulator automatically:

* sends 20 notification requests
* generates valid and invalid messages
* demonstrates routing behavior
* triggers dead-letter queue scenarios

---

# Expected Output

During execution, logs should appear across services:

### Dispatcher logs

```
message_received
message_dispatched
target_queue=email_high_queue
```

### Worker logs

```
notification_processing
notification_delivered
```

### Invalid requests

```
INVALID_CHANNEL
INVALID_PRIORITY
dead_letter_queue
```

These confirm correct routing behavior and failure handling.

---

# Failure Scenario Demonstration

The simulator intentionally generates invalid requests:

```
channel = fax
priority = urgent
```

These messages are automatically redirected to the Dead Letter Queue.

This demonstrates:

* input validation
* scheduler protection logic
* fault isolation capability
* pipeline resilience

---

# Observability Endpoints

Dispatcher monitoring:

```
http://localhost:8001/health
http://localhost:8001/metrics
```

Gateway monitoring:

```
http://localhost:8000/health
```

These endpoints provide runtime visibility into system status and routing performance.

---

# Execution Order Summary

Always launch services in this sequence:

```
1 Start RabbitMQ
2 Start Dispatcher
3 Start Gateway
4 Start Workers
5 Run Simulator
```

Incorrect startup order may prevent queue connections from initializing correctly.
