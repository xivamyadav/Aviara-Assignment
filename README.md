# Lead Automation System

Backend service and automation pipeline for lead enrichment, classification, and processing. Built for production workloads with FastAPI and n8n.

---

## Setup Instructions

**Prerequisites:**
- Python 3.11+
- Gemini API key
- Docker (optional)

### Local Dev

```bash
git clone <repo-url>
cd aviara

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
# Edit .env and supply GEMINI_API_KEY
```

Run server:
```bash
uvicorn app.main:app --reload --port 8000
```
Swagger UI available at: `http://localhost:8000/docs`

### Docker

```bash
copy .env.example .env
docker-compose up --build
```

---

## Architecture & Workflows

```
Webhook
  │
  ▼
Validation 
  │
  ├── /enrich  (Company size/industry heuristics + Redis caching)
  │
  ├── /classify (Gemini-2.0-flash intent extraction API with explicit Keyword fallback)
  │
  ├── Storage (SQLite internal leads and queue)
  │
  └── Notification (Async background webhook to Slack/etc)
```

**Key System Specs**
- **Fallback**: Classifier handles missing keys or 429 quota exhaustion transparently using a deterministic keyword map.
- **Bonus additions built**: Redis caching layer on enrichment, Idempotency checks on all commits, Dead-letter DB table for failures, Docker support, API key header auth, background task notification execution.

---

## Endpoints

(All endpoints require `X-API-Key` header. Default: `ase-lead-automation-2024`)

### `POST /enrich`
Resolves company domain to sizes/industries and generates linkedin URLs.

### `POST /classify`
Analyzes inbound lead request and parses an intent. Valid intents: `sales_enquiry`, `support_request`, `partnership`, `job_application`, `spam`, `general_inquiry`.

### `POST /webhook/lead`
Runs the entire local process synchronously (validates -> enriches -> classifies -> stores -> notifies).

---

## Testing

```bash
pytest tests/ -v
```

---

## n8n Setup

- Import `n8n/workflow.json` into your local n8n.
- Enable the workflow and you're good to go.
