# AcadEval+

AcadEval+ is a graph-based academic project assessment prototype. A submission is parsed, classified, converted into structured entities, compared with the historical project graph, and presented to faculty as an explainable novelty report. Faculty remain the final decision-makers and their ratings form the validation dataset.

## Stage 1 status

The application now uses the real FastAPI/PostgreSQL/Neo4j flow. Browser-side mock
responses and fabricated evaluation records have been removed.

Implemented foundation:

- React/Vite frontend with a successful production TypeScript build
- FastAPI authentication, projects, reports, appeals, rubrics, viva, and graph routes
- PostgreSQL persistence and Alembic migrations
- Redis/Celery asynchronous processing and Celery Beat
- Neo4j with APOC and Graph Data Science plugins
- GROBID service for citation parsing
- Persistent batch-upload tracking
- Read-only persisted novelty report retrieval
- Upload type, MIME, size, mode, and abstract word-count validation

The remaining scoring engines and publication-grade validation work are tracked for later stages. A score is not fabricated when an engine or dependency fails.

## One-command development stack

Requirements: Docker Desktop with Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

On Windows PowerShell you can run:

```powershell
Copy-Item .env.example .env
.\start.ps1
```

Before starting, set `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, and
`NEO4J_PASSWORD` in `.env`. Use a random `JWT_SECRET` of at least 32 characters.
To create the first HOD account, set `BOOTSTRAP_ADMIN_NAME`,
`BOOTSTRAP_ADMIN_EMAIL`, and a unique `BOOTSTRAP_ADMIN_PASSWORD` of at least
12 characters. Leave the email blank to skip bootstrapping. External API and
SMTP credentials are optional.

The optional bootstrap account is created idempotently. No sample projects,
labels, scores, or browser-side evaluation records are generated.

Services:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474
- GROBID: http://localhost:8070

Stop the stack with:

```bash
docker compose down
```

Add `-v` only when you intentionally want to delete all local PostgreSQL, Redis, Neo4j, and uploaded-file volumes.

## Local frontend verification

```bash
npm ci
npm run build
npm run lint
```

## Database migrations

The API container runs `alembic upgrade head` before starting FastAPI. For a manually managed backend:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Repository layout

```text
acadeval/
├── backend/          FastAPI, Celery, Alembic, scoring and graph services
├── datasets/         Taxonomy, feature KB, corpus and benchmark inputs
├── src/              React frontend
├── docker-compose.yml
└── .env.example      Safe configuration template
```

## Security note

Never commit `.env`. If a real key was previously committed, removing the file from the current branch is not sufficient: revoke or rotate the credential and remove it from Git history before publishing the repository.
