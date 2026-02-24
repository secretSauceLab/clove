
# clove

A FastAPI intake API for patient advocacy case management. Clove is the internal intake layer that powers Cinnamon's case pipeline; handling everything from first contact with a patient to document processing, status tracking, and case notes.

Named after the spice.

---

## What it does

- Accepts patient intake forms and creates advocacy cases
- Tracks case status through a defined workflow (NEW → IN_REVIEW → SUBMITTED → APPROVED, and so on)
- Stores case notes, documents, and a full status event audit trail
- Processes documents asynchronously via background tasks
- Enforces valid status transitions so nobody accidentally approves a case that hasn't been reviewed (we checked)

---

## Stack

- **Python 3.11** + **FastAPI**
- **PostgreSQL** via SQLAlchemy 2.0 (async)
- **Alembic** for migrations
- **Docker + Docker Compose** for local development
- **Google Cloud Run + Cloud SQL** in production (eventually)

---

## Getting started

### Prerequisites

- Docker
- Docker Compose

That's it. You don't need Python, Postgres, or anything else installed locally.

### Run it
```bash
cp .env.example .env       # fill in your values
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
| `DATABASE_URL` | Full Postgres connection string. Overrides individual DB vars. | — |
| `DB_HOST` | Postgres host. Use `/cloudsql/<connection>` for Cloud SQL. | `localhost` |
| `DB_NAME` | Database name. | `advocacy` |
| `DB_USER` | Database user. | `advocacy` |
| `DB_PASSWORD` | Database password. | — |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size. | `5` |
| `DB_MAX_OVERFLOW` | Max overflow connections above pool size. | `2` |

---

## API overview

All endpoints require an `X-API-Key` header. No key, no data. Gerald understands.

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

37 tests. All passing. Gerald's hammock claim is fully covered.

Tests use an in-memory SQLite database with transaction rollback isolation — no Postgres required, no cleanup needed, finishes in under a second.

---

## Project structure
```
app/
  routers/          # one file per domain (intakes, cases, notes, documents)
  models.py         # SQLAlchemy ORM models
  schemas.py        # Pydantic request/response schemas
  db.py             # async engine, session factory, settings
  auth.py           # API key authentication
  jobs.py           # background document processing
  enqueue.py        # background task dispatcher
alembic/
  versions/         # migration history
tests/
  conftest.py       # shared fixtures
  test_*.py         # one file per router
```

---

## A note on security

This API handles patient data. A few things worth knowing:

- API key comparison uses `hmac.compare_digest()` to prevent timing attacks
- Status transitions are enforced server-side — the client cannot skip steps
- Document processing happens asynchronously after commit, never before
- All datetimes are timezone-aware UTC

If you see something that looks wrong, say something. Healthcare is regulated for a reason.
