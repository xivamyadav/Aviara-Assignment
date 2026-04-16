# System Design — Lead Automation Pipeline

## Overview

This document covers how the lead automation system handles scale, failures, and overall architecture. The current implementation is built for reliability at moderate volume, with a clear upgrade path to handle high throughput.

---

## 1. Scalability

### Current Design
- FastAPI with async handlers — non-blocking I/O means a single instance can handle many concurrent requests
- SQLite works great for demos and low-moderate volume (up to ~500 leads/hour on a single instance)

### Scaling to 1000+ Leads/Hour

**Step 1: Add a message queue**

Instead of processing leads synchronously in the API handler, push them into a Redis queue:

```
Webhook → FastAPI (validates, acks immediately) → Redis Queue → Celery Workers → DB + Notifications
```

- The API responds instantly (202 Accepted) after validation
- Workers pick up leads from the queue and process them independently
- This decouples ingestion from processing

**Step 2: Horizontal scaling**

- Run multiple FastAPI instances behind a load balancer (nginx / AWS ALB)
- Scale Celery workers independently based on queue depth
- Swap SQLite for PostgreSQL for concurrent write support

**Step 3: Batch processing**

- Accumulate leads in small batches (e.g., 10-50) before hitting the enrichment/classification APIs
- Reduces per-request overhead and helps with rate limits on external APIs

### Worker Isolation Strategy

Each Celery worker runs as its own process with:
- Separate DB connection pool
- Independent retry state
- Configurable concurrency (prefork or eventlet depending on I/O vs CPU load)

If a worker crashes, the message stays in Redis and another worker picks it up.

---

## 2. Reliability

### Retry Mechanisms

| Component | Retry Strategy |
|-----------|---------------|
| Enrichment API call | 3 retries, 2s interval (in n8n or service) |
| Classification API call | 3 retries, 2s interval |
| Notification webhook | 3 retries with exponential backoff |
| Celery tasks (future) | Auto-retry with max_retries=5, exponential backoff |

### Dead-Letter Queue

Failed leads that exhaust all retries go into the `dead_letter_leads` table:
- Stores the full original payload
- Records the error message
- Tracks retry count
- Easy to query and re-process later

### Idempotency

- Every lead gets an idempotency key (either from the `X-Idempotency-Key` header or auto-generated from email + date)
- Duplicate requests with the same key return the existing result instead of re-processing
- Prevents double-processing when webhooks retry

### Rate Limiting

For production, add rate limiting at two levels:
1. **API Gateway** — limit inbound requests per IP/key (e.g., 100 req/min)
2. **Outbound calls** — throttle enrichment and classification API calls if using external services with rate limits

Can be implemented with `slowapi` (FastAPI middleware) or at the nginx level.

---

## 3. Architecture

### High-Level Flow

```
                    ┌──────────────┐
                    │   Webhook    │
                    │  (n8n / API) │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    │   Gateway    │
                    │              │
                    │ • Validate   │
                    │ • Auth       │
                    │ • Rate Limit │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌───────────┐ ┌──────────┐ ┌──────────┐
       │  Enrich   │ │ Classify │ │  Store   │
       │  Service  │ │ Service  │ │ Service  │
       │           │ │ (Gemini) │ │ (SQLite/ │
       │ • Domain  │ │          │ │  Postgres)│
       │   lookup  │ │ • LLM    │ │          │
       │ • Heuristic│ │ • Fallback│ │ • Leads  │
       └───────────┘ └──────────┘ │ • Dead   │
                                   │   Letter │
                                   └──────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Notification │
                    │   Service    │
                    │              │
                    │ • Webhook    │
                    │ • Slack      │
                    │ • Email      │
                    └──────────────┘
```

### Production Architecture (Scaled)

```
                         ┌───────────┐
                         │   nginx   │
                         │   (LB)    │
                         └─────┬─────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                    ▼          ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ FastAPI  │ │ FastAPI  │ │ FastAPI  │
              │ Worker 1 │ │ Worker 2 │ │ Worker N │
              └────┬─────┘ └────┬─────┘ └────┬─────┘
                   │             │             │
                   └─────────────┼─────────────┘
                                 │
                          ┌──────▼──────┐
                          │    Redis    │
                          │   (Queue +  │
                          │   Cache)    │
                          └──────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Celery  │ │  Celery  │ │  Celery  │
              │ Worker 1 │ │ Worker 2 │ │ Worker N │
              └────┬─────┘ └────┬─────┘ └────┬─────┘
                   │             │             │
                   └─────────────┼─────────────┘
                                 │
                          ┌──────▼──────┐
                          │ PostgreSQL  │
                          └─────────────┘
```

### Key Design Decisions

1. **Gemini with fallback** — If the API key is missing or the call fails, the system gracefully degrades to keyword-based classification. No single point of failure.

2. **Background notifications** — Notification sending happens via FastAPI's BackgroundTasks so the API response isn't blocked by slow external webhooks.

3. **Dead-letter queue in DB** — Simple, queryable, no extra infrastructure needed. For production, could be backed by Redis or RabbitMQ.

4. **Idempotency by design** — Webhook retries are expected. The system handles them without creating duplicates.

5. **Separation of concerns** — Routers handle HTTP, services handle logic, models handle data. Easy to test each layer independently.
