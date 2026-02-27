# Clove

A FastAPI API for patient advocacy case management with a prior authorization pipeline. Handles intakes, case tracking, document processing, and answering insurance questionnaires using FHIR records and Gemini.

Named after the spice.

---

## What it does

- Accepts patient intake forms and creates advocacy cases
- Tracks case status through a defined workflow (NEW → IN_REVIEW → SUBMITTED → APPROVED, and so on)
- Stores case notes, documents, and a full status event audit trail
- Processes documents asynchronously via background tasks
- Enforces valid status transitions so nobody accidentally approves a case that hasn't been reviewed
- **Processes prior authorization requests asynchronously via a pub/sub pipeline**
- **Classifies FHIR R4 record relevance using Gemini structured output (Pydantic schemas)**
- **Answers insurance questionnaires using Gemini with supporting record citations**

---

## Prior Authorization Pipeline

The most time-consuming part of patient advocacy is filling out insurance prior auth questionnaires. Nurses dig through medical records to answer questions like "Has the patient tried and failed first-line therapy?" — for every patient, every drug, every submission.

Clove automates most of this:

1. Nurse submits a prior auth request with the condition, drug, and questionnaire questions
2. API returns 202 (Accepted) immediately
3. Pipeline processes asynchronously through four pub/sub stages:
   - **Fetch** FHIR records from the hospital EHR
   - **Classify** — strip interoperability plumbing, then use Gemini structured output to classify each record's relevance to the condition/drug, convert relevant records to natural language
   - **Answer** — Gemini answers each question and cites supporting records
   - **Notify** — alert the nurse that results are ready
4. Nurse reviews answers and supporting records before submission to insurance

Classification uses Gemini with structured output (Pydantic response schemas) instead of a trained model. Each classification comes back as `relevant: true/false` with reasoning. Nurse corrections on the results become labeled training data — the plan is to eventually train a custom classifier once there's enough data.

Pub/sub is local right now (asyncio queues) but structured to swap to Google Cloud Pub/Sub without changing the pipeline logic. FHIR records come from Synthea.

---

## Stack

- **Python 3.11** + **FastAPI**
- **PostgreSQL** via SQLAlchemy 2.0 (async)
- **Alembic** for migrations
- **Google Gemini** (gemini-2.5-flash) via the google-genai SDK
- **Docker + Docker Compose** for local development
- **Google Cloud Run + Cloud SQL** for deployment

---

## Getting started

### Prerequisites

- Docker
- Docker Compose

That's it. You don't need Python, Postgres, or anything else installed locally.

### Run it
```bash
cp .env.example .env       # fill in your values (API_KEY, GEMINI_API_KEY)
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Verify it's alive
```bash
curl http://localhost:8000/health
# {"status":"oh yeah, we good"}
```

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Required. Shared secret for API authentication. | — |
| `GEMINI_API_KEY` | Required for prior auth pipeline. Google AI API key. | — |
| `DATABASE_URL` | Full Postgres connection string. Overrides individual DB vars. | — |
| `DB_HOST` | Postgres host. Use `/cloudsql/<connection>` for Cloud SQL. | `localhost` |
| `DB_NAME` | Database name. | `advocacy` |
| `DB_USER` | Database user. | `advocacy` |
| `DB_PASSWORD` | Database password. | — |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size. | `5` |
| `DB_MAX_OVERFLOW` | Max overflow connections above pool size. | `2` |

---

## API overview

All endpoints require an `X-API-Key` header.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/intakes` | Submit a new patient intake |
| `GET` | `/cases` | List cases (filterable by status, assignee) |
| `GET` | `/cases/{id}` | Get full case detail with applicant, notes, and status history |
| `PATCH` | `/cases/{id}` | Update case status or assignee |
| `POST` | `/cases/{id}/notes` | Add a note to a case |
| `GET` | `/cases/{id}/notes` | List notes for a case |
| `POST` | `/cases/{id}/documents` | Upload a document reference |
| `GET` | `/cases/{id}/documents` | List documents for a case |
| `POST` | `/prior-auth` | Submit a prior authorization request (returns 202) |
| `GET` | `/prior-auth/{id}` | Check status and results of a prior auth request |
| `GET` | `/health` | Health check |

### Case status workflow

Cases move through a defined set of states. Not all transitions are legal — the API will tell you if you try something inadvisable.
```
NEW → IN_REVIEW → NEEDS_INFO → IN_REVIEW (loop until ready)
              ↓
          SUBMITTED → APPROVED → CLOSED
                    → DENIED  → CLOSED
```

Any state can transition to `CLOSED`. Because sometimes that's just how it goes.

---

## Running migrations
```bash
# Apply all pending migrations
docker compose exec api alembic upgrade head

# Generate a new migration after model changes
docker compose exec api alembic revision --autogenerate -m "describe your change"

# Roll back one migration
docker compose exec api alembic downgrade -1
```

---

## Running tests
```bash
docker compose exec api pytest tests/ -v
```

Tests use an in-memory SQLite database with transaction rollback isolation — no Postgres required, no cleanup needed, finishes in under a second.

---

## Project structure
```
app/
  routers/              # one file per domain
    intakes.py
    cases.py
    notes.py
    documents.py
    internal.py
    prior_auth.py       # prior auth API endpoints
  models.py             # SQLAlchemy ORM models (cases, applicants, notes, documents)
  models_prior_auth.py  # prior auth request + answer models
  schemas.py            # Pydantic request/response schemas
  schemas_prior_auth.py # prior auth schemas
  db.py                 # async engine, session factory, settings
  auth.py               # API key authentication
  pubsub.py             # local pub/sub (swappable to Google Cloud Pub/Sub)
  fhir.py               # FHIR R4 processing: strip plumbing, Gemini structured output classification, NL conversion
  subscribers.py        # pipeline stage handlers + Gemini integration
  jobs.py               # background document processing
  enqueue.py            # background task dispatcher
alembic/
  versions/             # migration history
data/
  sample_patient.json   # Synthea-generated FHIR R4 patient bundle (684 resources)
tests/
  conftest.py           # shared fixtures
  test_*.py             # one file per domain
```

---

## A note on security

This API handles patient data. A few things worth knowing:

- API key comparison uses `hmac.compare_digest()` to prevent timing attacks
- Status transitions are enforced server-side — the client cannot skip steps
- Document processing happens asynchronously after commit, never before
- All datetimes are timezone-aware UTC
- Docker container runs as a non-root user
- Global exception handler prevents stack trace leakage
- API keys and credentials are loaded from environment variables, never committed

If you see something that looks wrong, say something. Healthcare is regulated for a reason.
