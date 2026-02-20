# Clove — Patient Advocacy Intake API

Clove is a small **Patient Advocacy Intake API** built with **FastAPI + Postgres + SQLAlchemy + Alembic**.  
It’s intentionally scoped to be easy to understand, easy to deploy, and easy to demo.

**Core workflow**
- **Intakes** create **Cases**
- Cases can have **status events**, **notes**, and **documents (metadata)**
- Documents can be “processed” via an internal endpoint (stubbed for now)

---

## Features

- FastAPI REST API
- Postgres persistence (SQLAlchemy 2.x)
- Alembic migrations
- API key auth via `X-API-Key`
- Docker Compose local dev
- Cloud Run + Cloud SQL deployment
- Secret Manager for credentials

---

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy (sync)
- Alembic
- Postgres 16 (local + Cloud SQL)
- Docker / Docker Compose
- Google Cloud Run, Cloud SQL, Artifact Registry, Secret Manager

---

## Authentication

Most endpoints require an API key:

```
X-API-Key: <your-api-key>
```

Locally, set `API_KEY` in your environment (or `.env`).  
In production, store it in Secret Manager and map it to the `API_KEY` environment variable.

---

## Endpoints (High Level)

**Public**
- `POST /intakes` — create an intake (creates a new case)
- `GET /cases` — list cases (pagination supported)
- `GET /cases/{case_id}` — case detail
- `PATCH /cases/{case_id}` — update case status/assignee
- `POST /cases/{case_id}/notes` — add a note
- `GET /cases/{case_id}/notes` — list notes
- `POST /cases/{case_id}/documents` — add a document (metadata)
- `GET /cases/{case_id}/documents` — list documents

**Internal**
- `POST /internal/documents/{document_id}/process` — trigger document processing (stub)

To see the full contract:
- `GET /openapi.json`

---

## Local Development (Docker Compose)

### Prereqs
- Docker + Docker Compose

### 1) Start services
From the repo root:

```bash
docker compose up --build
```

### 2) Run migrations
In another terminal:

```bash
docker compose exec api alembic upgrade head
```

### 3) Verify health
```bash
curl -s http://localhost:8080/health
```

Expected:
```json
{"status":"ok"}
```

---

## Local Configuration

This app supports either:
- `DATABASE_URL` (preferred), or
- discrete vars: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### Example: DATABASE_URL (local compose)
```bash
export DATABASE_URL="postgresql+psycopg://advocacy:advocacy@db:5432/advocacy"
```

### Example: discrete vars
```bash
export DB_HOST="db"
export DB_NAME="advocacy"
export DB_USER="advocacy"
export DB_PASSWORD="advocacy"
```

---

## Quick Local Usage (curl)

> Replace `API_KEY` if your local config requires it.

```bash
API_KEY="dev-secret"
BASE_URL="http://localhost:8080"
```

### Create an intake (creates a case)
```bash
curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{
    "full_name":"Test Patient",
    "email":"test@example.com",
    "narrative":"hello from local"
  }'   "$BASE_URL/intakes"
```

### List cases
```bash
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/cases"
```

### Add a note
```bash
CASE_ID=1

curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{"author":"Jeremy","body":"First note"}'   "$BASE_URL/cases/$CASE_ID/notes"
```

### List notes
```bash
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/cases/$CASE_ID/notes"
```

### Add a document (metadata)
```bash
curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{"filename":"denial_letter.pdf","content_type":"application/pdf"}'   "$BASE_URL/cases/$CASE_ID/documents"
```

### List documents
```bash
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/cases/$CASE_ID/documents"
```

---

## Production (Cloud Run)

This deployment setup uses:
- **Artifact Registry** for images
- **Cloud Run** for hosting
- **Cloud SQL (Postgres)** for the database
- **Secret Manager** for API key + DB password

### Environment Variables (Cloud Run)

Typical values in Cloud Run:

- `DB_HOST` = `/cloudsql/<PROJECT>:<REGION>:<INSTANCE>`
- `DB_NAME` = `advocacy`
- `DB_USER` = `advocacy`
- `DB_PASSWORD` = from Secret Manager (`CLOVER_DB_PASSWORD`)
- `API_KEY` = from Secret Manager (`CLOVER_API_KEY`)

---

## Production Smoke Test (Cloud Run)

This is the “does prod actually work?” checklist you can run after deploy.

### Prereqs
- `gcloud` authenticated and set to the correct project
- `python3` available (for pretty JSON)
- `CLOVER_API_KEY` stored in Secret Manager

### 0) Set URL + API key
```bash
REGION="us-west1"
SERVICE="clove-api"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
API_KEY="$(gcloud secrets versions access latest --secret=CLOVER_API_KEY)"

echo "URL=$URL"
```

### 1) Health check
```bash
curl -s "$URL/health" | python3 -m json.tool
```

Expected:
```json
{"status":"ok"}
```

### 2) Create an intake (creates a case)
```bash
curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{
    "full_name":"Prod Smoke",
    "email":"prod-smoke@example.com",
    "narrative":"hello from prod"
  }'   "$URL/intakes" | python3 -m json.tool
```

Expected shape:
```json
{"case_id": 123, "status": "NEW"}
```

Set:
```bash
CASE_ID=123
```

### 3) List cases
```bash
curl -s -H "X-API-Key: $API_KEY" "$URL/cases" | python3 -m json.tool
```

### 4) Add a note
```bash
curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{"author":"prod-smoke","body":"First note from prod"}'   "$URL/cases/$CASE_ID/notes" | python3 -m json.tool
```

Expected shape:
```json
{"note_id": 1, "case_id": 123}
```

### 5) List notes
```bash
curl -s -H "X-API-Key: $API_KEY" "$URL/cases/$CASE_ID/notes" | python3 -m json.tool
```

### 6) Add a document (metadata)
```bash
curl -s -H "X-API-Key: $API_KEY"   -H "Content-Type: application/json"   -d '{"filename":"denial_letter.pdf","content_type":"application/pdf"}'   "$URL/cases/$CASE_ID/documents" | python3 -m json.tool
```

Expected shape:
```json
{"document_id": 1, "case_id": 123, "status": "UPLOADED"}
```

Set:
```bash
DOCUMENT_ID=1
```

### 7) Trigger processing (internal endpoint)
```bash
curl -s -X POST -H "X-API-Key: $API_KEY"   "$URL/internal/documents/$DOCUMENT_ID/process" | python3 -m json.tool
```

---

## Alembic + Cloud SQL Notes (Important)

If you see errors like:

- `relation "documents" does not exist`

…it means your Cloud SQL database is missing migrations.

### Run Alembic against Cloud SQL via Cloud SQL Proxy

1) Start the proxy (local machine)
```bash
PROJECT_ID="$(gcloud config get-value project)"
REGION="us-west1"
INSTANCE="clove-pg"

CONNECTION_NAME="$(gcloud sql instances describe "$INSTANCE" --format='value(connectionName)')"
cloud-sql-proxy "$CONNECTION_NAME" --port 5433
```

2) Run migrations from inside the Docker `api` container using the proxy
```bash
DB_PASSWORD="$(gcloud secrets versions access latest --secret=CLOVER_DB_PASSWORD)"
DATABASE_URL="postgresql+psycopg://advocacy:${DB_PASSWORD}@host.docker.internal:5433/advocacy"

docker compose exec -e DATABASE_URL="$DATABASE_URL" api alembic upgrade head
```

3) Verify tables exist (requires `psql`)
```bash
psql "postgresql://advocacy:${DB_PASSWORD}@127.0.0.1:5433/advocacy" -c "\dt"
```

---

## Troubleshooting

### `Method Not Allowed`
You used the wrong HTTP method for the route (e.g., `GET` vs `POST`).  
Check:
- `GET /openapi.json`

### 500s in Cloud Run but no app logs
Request logs show up under `run.googleapis.com/requests`.  
Your stdout/stderr logs show up under:
- `run.googleapis.com/stdout`
- `run.googleapis.com/stderr`

### Container failed to start on Cloud Run
Usually a Python import error or app boot error.  
Check revision logs and ensure your container listens on port `8080`.

---

## License
MIT (or your preference)
