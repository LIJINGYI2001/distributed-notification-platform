

# Distributed Notification Platform

This project implements a distributed notification routing system based on RabbitMQ.
It demonstrates asynchronous message delivery, priority-based scheduling, failure handling, and observability within a modular distributed architecture.

Course:
ENGR 5710G – Network Computing (Winter 2026)

Instructor:
Dr. Qusay H. Mahmoud

Group Members:
Jingyi Li – 100996023
Yujie Lin – 100993827
Quan Yuan – 100987908

## System Overview

The system supports notification delivery through multiple communication channels:

* Email
* Push notification
* In-app notification

It demonstrates:

* asynchronous message routing
* queue-based communication
* worker concurrency
* dead-letter queue failure handling
* structured logging and metrics monitoring

## Architecture

Client → API Gateway → Dispatcher → RabbitMQ → Worker Services → Monitoring

## Components

### API Gateway

Receives notification requests and publishes validated messages to the incoming queue.

### Dispatcher Service

Consumes messages from the incoming queue and routes them to channel-specific and priority-specific worker queues.

### Worker Services

Three independent workers process messages asynchronously:

* Email worker
* Push worker
* In-app worker

### Monitoring Module

Provides runtime visibility through:

* `/health`
* `/metrics`

## Concurrency Model

Parallel processing is achieved through independent worker services consuming:

* `email_high_queue`
* `email_normal_queue`
* `push_high_queue`
* `push_normal_queue`
* `inapp_high_queue`
* `inapp_normal_queue`

## Failure Handling

The system demonstrates:

* invalid channel rejection
* invalid priority rejection
* timeout simulation
* retry-based recovery
* dead-letter queue routing
* worker crash tolerance

## Project Structure

```text
project/
├── code/
│   ├── gateway/
│   ├── dispatcher/
│   └── workers/
├── report/
└── presentation/
```

## Requirements

Python 3.10+

Install dependencies:

```bash
pip install fastapi uvicorn pika requests pydantic
```

Start RabbitMQ:

```bash
sudo systemctl start rabbitmq-server
```

or

```bash
docker run -d rabbitmq:3-management
```

## Run Instructions

Start services in this order.

### Step 1 Start RabbitMQ

```bash
sudo systemctl start rabbitmq-server
```

### Step 2 Start Dispatcher

```bash
cd code/dispatcher
python main.py
```

### Step 3 Start Gateway

```bash
cd code/gateway
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 4 Start Workers

Email worker:

```bash
cd code/workers/email_worker
python worker_1.py
```

Push worker:

```bash
cd code/workers/push_worker
python worker_1.py
```

In-app worker:

```bash
cd code/workers/inapp_worker
python worker_1.py
```

### Step 5 Run Simulator

```bash
cd code/gateway
python simulator.py
```

## Observability

Dispatcher endpoints:

```text
GET /health
GET /metrics
```

## Educational Purpose

This project demonstrates distributed system design principles including asynchronous communication, routing-layer scheduling, failure isolation, retry mechanisms, and observability integration.
