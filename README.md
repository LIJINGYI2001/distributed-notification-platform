````markdown
# README  
## Distributed Notification Routing System  
**ENGR 5710G – Network Computing (Winter 2026)**

**Group 7**

**Members**
- Jingyi Li — 100996023
- Yujie Lin — 100993827
- Quan Yuan — 100987908

---

## 1. Project Overview

This project implements a distributed notification routing system using RabbitMQ.

The system workflow is:

**Client Simulator → API Gateway → RabbitMQ → Dispatcher → Workers**

The platform supports:
- multi-channel notification processing
- asynchronous message routing
- priority-based scheduling
- dead-letter handling for invalid messages
- distributed execution through independent worker services

Supported channels:
- `email`
- `push`
- `inapp`

Supported priorities:
- `high`
- `normal`

---

## 2. Mapping to Required Assignment Structure

The assignment requires the following structure:

- `client`
- `serviceA`
- `serviceB`

This project maps them as follows:

| Assignment Role | Actual Implementation |
|---|---|
| client | simulator |
| serviceA | API Gateway |
| serviceB | dispatcher + worker subsystem |

---

## 3. Directory Structure

```text
code/
├── client/
│   └── simulator.py
│
├── serviceA/
│   └── gateway/
│       └── main.py
│
└── serviceB/
    ├── dispatcher/
    │   └── main.py
    │
    └── worker/
        ├── pyproject.toml
        ├── poetry.lock
        ├── README.md
        └── code/
            ├── __init__.py
            ├── monitoring/
            ├── shared/
            └── workers/
                ├── base_worker.py
                ├── email_worker/
                │   ├── worker_1.py
                │   ├── worker_2.py
                │   ├── worker_high_1.py
                │   └── worker_high_2.py
                ├── push_worker/
                │   └── worker_1.py
                └── inapp_worker/
                    ├── worker_1.py
                    └── worker_2.py
````

---

## 4. Software Requirements

Before running the project, install the following software:

* Python 3.10 or above
* RabbitMQ
* Poetry

The following Python libraries are also required:

* `fastapi`
* `uvicorn`
* `pika`
* `requests`
* `pydantic`

Install them with:

```bash
pip install fastapi uvicorn pika requests pydantic
```

---

## 5. Important Notes Before Running

Please read this section carefully before starting the system.

### 5.1 Start Order Matters

The components must be started in this order:

1. RabbitMQ
2. Dispatcher
3. Gateway
4. Workers
5. Simulator

If this order is not followed, some components may fail to connect properly.

---

### 5.2 Worker Commands Must Be Run from the Correct Directory

All worker commands must be executed from:

```text
code/serviceB/worker
```

Do **not** run worker scripts directly from some other folder, otherwise Python import errors may occur.

For example, this is correct:

```bash
cd code/serviceB/worker
poetry run python code/workers/push_worker/worker_1.py
```

---

### 5.3 RabbitMQ Must Keep Running

RabbitMQ must remain active during the whole demo.
If RabbitMQ stops, dispatcher and workers will not be able to receive or publish messages.

---

## 6. Step-by-Step Run Instructions

This section explains exactly how to run the whole system.

---

### Step 1 — Start RabbitMQ

RabbitMQ is the message broker used by this project.

You can start RabbitMQ in one of the following ways.

#### Option A — Using Docker

Run:

```bash
docker run -d --hostname rabbitmq --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

This starts RabbitMQ and exposes:

* AMQP port: `5672`
* Management UI: `15672`

RabbitMQ management page:

```text
http://localhost:15672
```

Default username and password are usually:

```text
guest
guest
```

---

#### Option B — Local RabbitMQ Service

If RabbitMQ is already installed locally, start it using your system service manager.

Example on Linux:

```bash
sudo systemctl start rabbitmq-server
```

On Windows, RabbitMQ can be started through Services or RabbitMQ Server tools depending on installation.

---

### Step 2 — Start the Dispatcher

Open a new terminal.

Go to the dispatcher directory:

```bash
cd code/serviceB/dispatcher
```

Run:

```bash
python main.py
```

The dispatcher is responsible for:

* consuming messages from the incoming queue
* validating message channel and priority
* routing messages to worker queues
* redirecting invalid messages to the dead-letter queue

Keep this terminal open.

---

### Step 3 — Start the API Gateway

Open another new terminal.

Go to the gateway directory:

```bash
cd code/serviceA/gateway
```

Run:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The gateway should now be available at:

```text
http://localhost:8000
```

Useful endpoints:

* Health check:

  ```text
  http://localhost:8000/health
  ```

* Swagger UI:

  ```text
  http://localhost:8000/docs
  ```

* Main API endpoint:

  ```text
  POST /notifications
  ```

Keep this terminal open.

---

### Step 4 — Install Worker Dependencies

Open another terminal.

Go to the worker root folder:

```bash
cd code/serviceB/worker
```

Install Poetry dependencies:

```bash
poetry install
```

This usually only needs to be done once on a machine.

If dependencies are already installed, you may skip this step next time.

---

### Step 5 — Start Email Worker

Open a new terminal.

Go to the worker root folder:

```bash
cd code/serviceB/worker
```

Run one email worker:

```bash
poetry run python code/workers/email_worker/worker_1.py
```

If needed, you can also run additional email workers in separate terminals:

```bash
poetry run python code/workers/email_worker/worker_2.py
poetry run python code/workers/email_worker/worker_high_1.py
poetry run python code/workers/email_worker/worker_high_2.py
```

For a basic demo, running one or two email workers is usually enough.

Keep this terminal open.

---

### Step 6 — Start Push Worker

Open another new terminal.

Go to:

```bash
cd code/serviceB/worker
```

Run:

```bash
poetry run python code/workers/push_worker/worker_1.py
```

Keep this terminal open.

---

### Step 7 — Start In-App Worker

Open another new terminal.

Go to:

```bash
cd code/serviceB/worker
```

Run:

```bash
poetry run python code/workers/inapp_worker/worker_1.py
```

If needed, you can also start a second in-app worker in another terminal:

```bash
poetry run python code/workers/inapp_worker/worker_2.py
```

Keep this terminal open.

---

### Step 8 — Run the Client Simulator

Open another new terminal.

Go to the client folder:

```bash
cd code/client
```

Run:

```bash
python simulator.py
```

The simulator will automatically send notification requests to the gateway.

These requests will then flow through the whole system:

1. simulator sends request to gateway
2. gateway validates and publishes to RabbitMQ
3. dispatcher consumes from incoming queue
4. dispatcher routes to the correct worker queue
5. worker consumes and processes the notification

---

## 7. Recommended Demo Setup

For a clean demo, use the following terminal layout:

### Terminal 1

RabbitMQ

### Terminal 2

Dispatcher

```bash
cd code/serviceB/dispatcher
python main.py
```

### Terminal 3

Gateway

```bash
cd code/serviceA/gateway
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Terminal 4

Email worker

```bash
cd code/serviceB/worker
poetry run python code/workers/email_worker/worker_1.py
```

### Terminal 5

Push worker

```bash
cd code/serviceB/worker
poetry run python code/workers/push_worker/worker_1.py
```

### Terminal 6

In-app worker

```bash
cd code/serviceB/worker
poetry run python code/workers/inapp_worker/worker_1.py
```

### Terminal 7

Simulator

```bash
cd code/client
python simulator.py
```

---

## 8. How to Verify the System Is Working

You can verify the system step by step.

### 8.1 Check Gateway

Open:

```text
http://localhost:8000/health
```

You should see a health response indicating the gateway is running.

You can also open:

```text
http://localhost:8000/docs
```

to view the Swagger API interface.

---

### 8.2 Check Dispatcher Terminal

When messages are sent, the dispatcher terminal should show logs indicating:

* message received
* queue resolution
* routing result
* invalid message handling if applicable

---

### 8.3 Check Worker Terminals

Worker terminals should show processing logs such as:

* notification received
* notification processing
* delivered
* failed
* retried
* dead-letter handling

---

### 8.4 Check Simulator Output

The simulator terminal should print request results, showing whether requests were:

* successfully accepted
* rejected due to invalid channel or priority
* processed as expected

---

## 9. Expected Behavior

When the system is running correctly:

### Gateway

* receives client requests
* validates request body
* validates API key
* generates identifiers
* publishes messages to RabbitMQ

### Dispatcher

* consumes messages from `incoming_queue`
* checks message validity
* routes messages by channel and priority
* redirects unsupported messages to dead-letter handling

### Workers

* consume tasks asynchronously
* process delivery tasks independently
* simulate notification execution
* support retry and failure logging

### Simulator

* generates test workloads
* triggers valid and invalid scenarios
* helps demonstrate the complete distributed pipeline

---

## 10. Example Worker Queues

The system may use queues such as:

```text
incoming_queue
dead_letter_queue
email_high_queue
email_normal_queue
push_high_queue
push_normal_queue
inapp_high_queue
inapp_normal_queue
```

---

## 11. Common Problems and Fixes

### Problem 1 — `ModuleNotFoundError: No module named 'workers'`

Cause: worker script was started from the wrong folder.

Fix: always run worker commands from:

```text
code/serviceB/worker
```

Example:

```bash
cd code/serviceB/worker
poetry run python code/workers/push_worker/worker_1.py
```

---

### Problem 2 — `Not Found` in browser

Cause: user opened a POST endpoint directly in the browser.

Fix: use:

* Swagger UI at `http://localhost:8000/docs`, or
* the simulator, or
* a POST tool such as curl/Postman

Do not type `/POST/notifications` directly in the browser.

---

### Problem 3 — Worker or Dispatcher Cannot Connect to RabbitMQ

Cause:

* RabbitMQ is not running
* port is not available
* service started in wrong order

Fix:

1. start RabbitMQ first
2. verify port `5672` is active
3. restart dispatcher and workers after RabbitMQ is running

---

### Problem 4 — Simulator Sends Requests but Nothing Happens

Cause:

* gateway is not running
* dispatcher is not running
* workers are not running
* queue connections failed

Fix:

1. confirm gateway terminal is active
2. confirm dispatcher terminal is active
3. confirm worker terminals are active
4. rerun simulator after all services are up

---

## 12. Notes for the Grader

* `serviceA` corresponds to the API Gateway.
* `serviceB` contains both the dispatcher and the worker subsystem.
* Worker scripts are stored under:

```text
code/serviceB/worker/code/workers
```

* Worker commands must be run from:

```text
code/serviceB/worker
```

* RabbitMQ must be running before starting dispatcher, gateway, and workers.

---

## 13. Summary

This project demonstrates a distributed notification routing system with:

* asynchronous message delivery
* decoupled communication through RabbitMQ
* priority-aware queue routing
* independent worker execution
* failure isolation through dead-letter handling
* observable runtime behavior through logs and health checks

The system is designed as a course-scale distributed platform that is reproducible, modular, and easy to evaluate.

```
```
