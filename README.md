# Spoken Tutorial Generator

AI-powered platform for producing [Spoken Tutorial](https://spoken-tutorial.org/) content — outlines, scripts, slides, voice narration, images, and translations — from a simple course outline. Built for the Spoken Tutorial Project at IIT Bombay.

**Live:** [creation.edupyramids.org](https://creation.edupyramids.org) (sign-in restricted to `@edupyramids.org` Google accounts)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Data & Persistence](#data--persistence)
- [Background Jobs (Celery + Redis)](#background-jobs-celery--redis)
- [Key Workflows](#key-workflows)
- [API Reference](#api-reference)
- [Frontend](#frontend)
- [Deployment & CI/CD](#deployment--cicd)
- [Monitoring](#monitoring)
- [Development](#development)
- [Project Structure](#project-structure)
- [Further Documentation](#further-documentation)

---

## Overview

The Spoken Tutorial Generator is a full-stack application (FastAPI backend + React frontend) that automates the Spoken Tutorial content-authoring pipeline. It combines several LLM-driven workflows — outline interviews, script generation, compliance review, translation, and voice/image/slide generation — behind a single chat-style UI.

The platform runs as a **PostgreSQL-backed, containerised production system**:

- **PostgreSQL** stores users, chat threads, background-job records, and LangGraph checkpoints.
- **Celery + Redis** run long/heavy tasks (Whisper transcription) out-of-band from the API.
- **Alembic** manages the relational schema; LangGraph's `AsyncPostgresSaver` manages checkpoint tables.
- A dedicated **Whisper worker container** isolates the heavy speech-to-text dependency from the API image.
- **CI/CD builds images in GitHub Actions, ships them via GHCR**, and refuses to complete a deploy unless the stack reports healthy; rollback takes seconds.
- **Prometheus + Grafana** (provisioned entirely from files in this repo) provide request, job, and per-user activity dashboards.

---

## Features

| Feature | Description |
|:--------|:------------|
| **Script Chat** | Conversational, human-in-the-loop script authoring via a LangGraph state machine (ingest → grounding → metadata → generation → editing → compliance). Streams progress over SSE, pauses at review gates, supports manual edits, checkpoint/version history, revert, and stage jumps. Persisted per-user in PostgreSQL. |
| **Outline Chat** | Phased SME interview (warmup → outcomes → examples → structure → metadata → review) that builds a Spoken Tutorial course outline, with streaming SSE, field editing, validation, and PDF/JSON export. |
| **Script Generation** | LangGraph pipeline (metadata → parallel boilerplate + content → merge) that turns an outline into a structured JSON script. |
| **Slides Generation** | Beamer LaTeX slides, auto-populated from scripts via LLM content extraction, with a theme colour picker. |
| **Voice Generation** | Sarvam TTS — per-slide audio (ZIP) or a single combined tutorial audio, with optional pronunciation-dictionary correction for domain terms. |
| **Image Generation** | AI-enhanced prompts → image generation (Gemini), with prompt-review UI, reference-image upload, and per-image editing. |
| **Compliance** | Evidence-based admin-script compliance (`admin_script_v1` policy, 25 criteria) combining deterministic validators with LLM semantic + factuality checks, plus an admin review workspace. Pedagogy/quality compliance via back-translation. |
| **Translation** | Multi-language batch translation with an editable translation grid, per-cell TTS, and DOCX export. |
| **Slides Translation** | Translate `.tex` Beamer files to 11+ Indian languages with XeLaTeX Unicode support. |
| **Timed Script** | Upload audio/video → **background** Whisper transcription → sentence-level timestamps → DOCX export. Progress visible in the UI, restored on page reload. |
| **MediaWiki Export** | One-click export to Spoken Tutorial wiki table format (from JSON or DOCX, including from a Script Chat thread). |
| **Version Change Automation** | Scrapes spoken-tutorial.org → LLM + Tavily web search for version updates → splits long tutorials into 3–4 min fragments → tabulates old-vs-new comparison → exports to Google Sheets via Workload Identity Federation. |
| **Google OAuth** | Domain-restricted Google authentication issuing JWTs; stable per-user identity in PostgreSQL. |

---

## Architecture

![Production architecture](docs/diagrams/architecture.svg)

<details>
<summary>Diagram source (Mermaid)</summary>

```mermaid
flowchart TB
    B([Browser]) -->|HTTPS| N["Host nginx — TLS, Let's Encrypt"]
    N -->|"forwards to 127.0.0.1:8080"| F

    subgraph net ["Docker Compose network — only 127.0.0.1:8080 published"]
        F["frontend — nginx + React 19 SPA<br/>routes /api · /static · /output · /grafana<br/>SPA fallback for the rest"]
        A["backend — FastAPI<br/>uvicorn × WEB_CONCURRENCY (4)<br/>15 routers · 2 LangGraph graphs<br/>/metrics (multiprocess-aggregated)"]
        P[("PostgreSQL 16<br/>users · threads · jobs · checkpoints")]
        R[("Redis 7<br/>Celery broker only")]
        W["whisper-worker — Celery<br/>queue=whisper · concurrency=1<br/>Whisper base model baked in"]
        PR["Prometheus"]
        G["Grafana 12<br/>dashboards provisioned from git"]

        F -->|"/api/ → :8000"| A
        F -->|"/grafana/"| G
        A -->|"SQL (shared psycopg pool)"| P
        A -->|send_task| R
        R -->|consume| W
        W -->|"progress + result (JSONB)"| P
        A <-.->|shared uploads volume| W
        PR -.->|"scrape /metrics · 15 s"| A
        G -.-> PR
        G -.->|"grafana_ro (read-only)"| P
    end

    A --> X["External services<br/>OpenAI · Google Gemini · Sarvam TTS · Tavily<br/>Google Sheets (WIF) · LangSmith tracing"]
```

</details>

Key points:

- In production **only `127.0.0.1:8080` is published** on the host; PostgreSQL, Redis, Prometheus, and Grafana are reachable solely on the internal Compose network.
- A **single shared PostgreSQL connection pool** lives in `src/script_chat/persistence.py`; the `jobs` and `users` modules import it rather than opening their own.
- The **API image contains no Whisper/torch** — those live only in `docker/worker.Dockerfile`.
- **Redis is only the Celery broker** (no result backend); job results are stored in the `background_jobs.result` JSONB column.

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic v2, uvicorn |
| Async jobs | Celery 5, Redis 7 |
| Database | PostgreSQL 16, psycopg 3 (pooled), SQLAlchemy + Alembic (migrations), LangGraph `AsyncPostgresSaver` (checkpoints) |
| Frontend | React 19, Vite 7, React Router 6, Tailwind CSS v4, Radix UI (shadcn-style), `motion`, lucide-react, react-markdown |
| AI / LLM | OpenAI (`gpt-5.4-mini`, `gpt-5.2`, `gpt-5-nano` — Script Chat, semantic compliance, fallback), Google Gemini (`gemini-2.5-flash` — core generation nodes, prompt enhancement; `gemini-3-pro-image-preview` — images), Sarvam (TTS) |
| Search | Tavily API |
| Speech-to-text | OpenAI Whisper (local, `base` model, dedicated worker container) |
| PDF / Slides | LaTeX (Beamer / XeLaTeX), python-docx, ReportLab, PyMuPDF, pdfplumber |
| Video / Audio | FFmpeg, MoviePy, pydub |
| Auth | Google OAuth 2.0, python-jose (JWT) |
| Infra | Docker Compose (`compose.yaml` + dev override), GitHub Actions → GHCR → SSH deploy, nginx, Prometheus + Grafana 12 (provisioned as code) |
| Observability | Prometheus (multiprocess client), Grafana dashboards-as-code, LangSmith tracing (project `slide-generator`) |
| Package mgmt | uv (Python, `uv.lock`), npm (JS, `package-lock.json`) |

---

## Quick Start

### Prerequisites

- **Docker + Docker Compose** (Option A needs nothing else)
- For local processes (Option B): **Python 3.11** (project supports `>=3.10,<3.13`) via [uv](https://github.com/astral-sh/uv), **Node.js 20+**, **LaTeX** (`brew install --cask mactex-no-gui` / `apt install texlive-full texlive-xetex`), **FFmpeg**

### Option A — Docker Compose (recommended)

`compose.yaml` is the single source of truth for all eight services. To build images from source instead of pulling from GHCR, create a `compose.override.yaml` at the project root (**local-only — it is gitignored**, so a fresh clone will not have it); Compose picks it up automatically:

```yaml
services:
  migrate:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile

  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile

  whisper-worker:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile

  frontend:
    build:
      context: ./chatbot-ui
```

```bash
# 1. Create .env at the project root (see Configuration).
#    Compose refuses to start without POSTGRES_PASSWORD,
#    GRAFANA_ADMIN_PASSWORD and GRAFANA_DB_PASSWORD.

# 2. Build and start everything
docker compose up -d --build

# Stack: postgres, redis, migrate (one-shot), backend, whisper-worker,
#        frontend, prometheus, grafana   →  http://localhost:8080
```

The `migrate` service runs `python -m src.script_chat.migrate` (Alembic + LangGraph checkpoint setup); `backend` and `whisper-worker` wait for it to exit successfully before starting.

### Option B — Local processes

```bash
# --- Data services (if not already running) ---
docker compose up -d postgres redis

# --- Backend ---
uv sync                              # install Python deps
export DATABASE_URL=postgresql://spoken_tutorial:spoken_tutorial@localhost:5432/spoken_tutorial
export CELERY_BROKER_URL=redis://localhost:6379/0
uv run python -m src.script_chat.migrate    # create schema + checkpoint tables
uv run python -m src.api                     # API on http://localhost:8000

# --- Whisper worker (separate terminal; needs the extra dep group) ---
uv sync --extra whisper-worker
uv run celery -A src.workers.celery_app:celery_app worker \
  --loglevel=INFO --pool=prefork --concurrency=1 --queues=whisper

# --- Frontend (separate terminal) ---
cd chatbot-ui
npm install && npm run dev           # Vite dev server on http://localhost:5173
```

> **First-run note:** the API fails fast at startup if the schema is missing. Always run `python -m src.script_chat.migrate` before starting the API against a fresh database.

---

## Configuration

Configuration is read from environment variables (loaded from a `.env` file at the project root). Backend settings are validated in `src/api/config.py`. There is no committed `.env.example` — the tables below are the reference.

### Core

| Variable | Default | Description |
|:---------|:--------|:------------|
| `ENVIRONMENT` | `development` | `development` or `production`. Production disables `/docs`, tightens CORS, and **rejects weak `JWT_SECRET_KEY` values at boot**. |
| `DEBUG` | `false` | Enables request logging middleware |
| `DATABASE_URL` | `postgresql://spoken_tutorial:spoken_tutorial@localhost:5432/spoken_tutorial` | PostgreSQL DSN (app tables **and** LangGraph checkpoints). In Compose it is composed from the `POSTGRES_*` variables. |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `spoken_tutorial` / `spoken_tutorial` / **required** | Compose-level database bootstrap; `POSTGRES_PASSWORD` has no default. |
| `DATABASE_POOL_MIN_SIZE` / `DATABASE_POOL_MAX_SIZE` | `1` / `5` (backend), `2` (worker) | Connection pool bounds |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `10` | Pool checkout timeout |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker for background jobs |
| `WEB_CONCURRENCY` | `4` | uvicorn worker count for the backend container |
| `IMAGE_TAG` | `latest` | Which GHCR image tag Compose runs. **Written by the deploy pipeline** (`sha-<commit>`); doubles as the rollback pointer. |
| `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS` | `1800` | A timed-script job still `running` past this is treated as stuck and failed by the stale-job reaper. |
| `TIMED_SCRIPT_REAPER_INTERVAL_SECONDS` | `300` | Reaper cadence when run via `celery beat` (optional — the worker also reaps opportunistically on every job). |

> `PROMETHEUS_MULTIPROC_DIR` is set by `compose.yaml` (to a tmpfs), not by `.env` — see [Monitoring](#monitoring).

### Auth

| Variable | Description |
|:---------|:------------|
| `JWT_SECRET_KEY` | **Required.** Must be ≥32 chars in production (`openssl rand -hex 32`) |
| `JWT_ALGORITHM` | JWT signing algorithm (default `HS256`) |
| `JWT_EXPIRATION_HOURS` | Token lifetime (default `24`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |
| `ALLOWED_EMAIL_DOMAIN` | Restrict login to a domain (default `@edupyramids.org`) |
| `CORS_ORIGINS` | Comma-separated origins, or `*` |
| `FRONTEND_URL` | Frontend base URL (used in OAuth redirects) |

### AI / external services

| Variable | Used for |
|:---------|:---------|
| `OPENAI_API_KEY` | Script Chat nodes, semantic + factuality compliance checks (compliance skipped if unset), fallback LLM in core generation nodes |
| `GOOGLE_API_KEY` | Gemini text and image generation |
| `TAVILY_API_KEY` | Web search (outline chat, factuality, version-change pipeline) |
| `SARVAM_API_KEY` | Sarvam TTS voices |
| `SARVAM_PRONUNCIATION_DICT_ID` | Optional. Sarvam pronunciation dictionary (branding/jargon fixes) applied to every TTS request. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Sheets export (Version Change Automation) via Workload Identity Federation |

### Observability

| Variable | Used for |
|:---------|:---------|
| `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` | Grafana admin login (password **required** by Compose) |
| `GRAFANA_DB_PASSWORD` | Password of the read-only `grafana_ro` PostgreSQL role, expanded inside the provisioned datasource. **Required** by Compose. |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_ENDPOINT` / `LANGCHAIN_PROJECT` | Zero-code LLM tracing of all LangChain/LangGraph calls into the `slide-generator` LangSmith project |

> The frontend reads `VITE_API_URL` at build time (default `/api` in Docker, empty/proxy in dev).

---

## Data & Persistence

PostgreSQL holds four logical schemas:

| Table | Managed by | Purpose |
|:------|:-----------|:--------|
| `users` | Alembic (`20260711_02`) | Stable per-user identity (UUID). Upserts on `(provider, provider_subject)`, unique `email`. JWT `sub` = this UUID. |
| `script_chat_threads` | Alembic (`20260710_01`, re-owned in `_02`) | Script Chat threads: `thread_id`, owner `user_id` (FK), `current_stage`, `status`, `title`, soft-delete `archived_at`. |
| `background_jobs` | Alembic (`20260711_03`) | Durable job records: `id`, `user_id` (FK), `job_type`, `status` (`queued/running/completed/failed`), `celery_task_id`, `input_path`, `result` (JSONB), `progress`, `current_stage`, timestamps. |
| `checkpoints`, … | LangGraph `AsyncPostgresSaver.setup()` | Script Chat conversation state / version history (created by `migrate.py`, **not** Alembic). |

Migrations live in `migrations/versions/` and are applied by `python -m src.script_chat.migrate`, which runs `alembic upgrade head` and then sets up the LangGraph checkpoint tables.

---

## Background Jobs (Celery + Redis)

Long-running work is offloaded to Celery so the API stays responsive.

- **Enqueue:** `POST /timed-script/generate` streams the upload to disk, inserts a `background_jobs` row (`create_job`), then `celery_app.send_task("src.workers.tasks.process_timed_script", ...)` and records the Celery task id.
- **Worker:** `src/workers/tasks.py::process_timed_script` atomically claims the job (`queued → running`; duplicate deliveries become no-ops), runs Whisper transcription (`generate_timed_script`), then writes `completed` (with `result`) or `failed`. The upload is deleted only once the job reaches a terminal state.
- **Poll:** clients poll `GET /timed-script/jobs/{job_id}` (or list via `GET /timed-script/jobs`). Server-side paths are never exposed in responses.
- **Queue routing:** the timed-script task is routed to the `whisper` queue; the Whisper worker container consumes only that queue with `--concurrency=1` / `worker_prefetch_multiplier=1` (one heavy job at a time) and `--max-tasks-per-child=15` to bound native-library memory creep.
- **Crash recovery:** with `task_acks_late` + `task_reject_on_worker_lost`, a worker that dies mid-transcription has its task redelivered. The task is bound (`self.request.id`), so `claim_job` can re-claim its own `running` row on redelivery instead of leaving it stuck forever; the input file survives because it is deleted only on a terminal state. As a backstop, a **stale-job reaper** fails jobs that have been `running` past `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS` (run opportunistically on every job and, optionally, on a `celery beat` schedule) so the polling UI always terminates.
- **Deploy safety:** the worker container has `stop_grace_period: 300s`, so in-flight transcriptions finish before a deploy replaces it.

Celery config lives in `src/workers/celery_app.py`; job persistence in `src/jobs/persistence.py`.

> Timed Script is currently the only background-job type. Translation and other endpoints remain synchronous.

---

## Key Workflows

### Script Chat (`src/script_chat/`)

A checkpointed LangGraph state machine for conversational, human-in-the-loop script authoring:

![Script Chat state machine](docs/diagrams/script-chat-graph.svg)

<details>
<summary>Node list (text form)</summary>

```
START → ingest → ground → ground_review ⇄ ground_edit
                        → metadata → metadata_review ⇄ metadata_edit
                        → generate → script_review ⇄ edit
                        → compliance → compliance_review → END
```

</details>

- State (`ScriptChatState`): messages, raw outline, grounding report, metadata, script (slides), version counter, compliance/quality results, current stage.
- Human-in-the-loop **interrupts** at each `*_review` gate; the client resumes with `approve` or `edit` via `POST /script-chat/resume/{thread_id}`.
- Manual, zero-token slide edits while paused at `script_review` (`PUT /script-chat/edit`).
- Full **checkpoint/version history**, **revert** to a prior version, and **stage jumps**.
- Per-user ownership enforced against `script_chat_threads` before any graph state is touched.

### Outline Chat (`src/api/routes/outline_chat/`, 14 submodules)

A phased SME interview that produces a compliant course outline:

```
Warmup → Outcomes → Examples → Structure → Metadata → Review → Approved
```

Streaming SSE, general chat with Tavily web search, snapshot endpoint, and PDF/JSON export.

### Script Generation Pipeline (`src/core/agent.py`)

A stateless 4-node graph with one parallel fan-out/fan-in — `generate_boilerplate` and `generate_content` run concurrently off the extracted metadata:

```
START → extract_metadata ──┬──→ generate_boilerplate ──┐
                            └──→ generate_content ──────┴──→ merge_script → END
```

(An evaluator/retry node exists under `src/nodes/_archive/` but is **not** wired into the active graph.)

### Admin Compliance (`src/compliance/`)

Evidence-anchored review of a generated script against `ADMIN_SCRIPT_POLICY_V1` (25 criteria):

- **Deterministic validators** — two-column format, required metadata, section presence, duration (4–5 min), row granularity, sentence length limits, and live link checking.
- **Semantic validators** — LLM checks (`gpt-5.2`) for structure/flow, visual-demo alignment, language quality, terminology, and a source-backed **factuality** pass (two-stage web-search + structured conversion). Skipped entirely if `OPENAI_API_KEY` is unset.
- Produces a structured `ComplianceReport` with per-cell annotations and severity summary. Invoked by both the compliance router and the Script Chat `compliance` node.

### Version Change Automation (`src/workflow.py` + `src/nodes/`)

```
FOSS + Language → extract_links → extraction (scrape) → updates (LLM + Tavily)
              → split (long tutorials) → tabulate (old-vs-new) → gsheet (export)
```

Exports an old-vs-new comparison table to Google Sheets via Workload Identity Federation.

---

## API Reference

All application endpoints (except `/`, `/health`, `/metrics`, and the `/auth/*` flow) require a `Bearer` JWT. Interactive docs are served at `/docs` in development only.

### System

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/` | GET | Service info |
| `/health` | GET | Health check (verifies PostgreSQL pool; 503 if unhealthy) |
| `/metrics` | GET | Prometheus metrics (aggregated across uvicorn workers) |

### Authentication (`/auth`)

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/auth/google` | GET | Initiate Google OAuth |
| `/auth/google/callback` | GET | OAuth callback → issues JWT |
| `/auth/verify` | POST | Verify JWT |
| `/auth/logout` | POST | Logout |

### Upload & Parse

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/upload_outline` | POST | Parse outline file (.md/.docx/.txt/.odt) |
| `/parse_script` | POST | Parse script only |
| `/upload_script` | POST | Parse script + run compliance |

### Generation

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/generate_script` | POST | Outline → JSON script (LangGraph pipeline) |
| `/generate_slides` | POST | JSON script → Beamer LaTeX + ZIP |
| `/generate_video` | POST | Script + PDF → narrated video |
| `/upload_edited_script` | POST | Upload edited .docx → JSON |
| `/export_mediawiki` / `/docx_to_mediawiki` | POST | → MediaWiki table |
| `/download_script_docx` | POST | JSON → editable Word doc |

### Compliance & Quality

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/check_compliance` | POST | Compliance check on a script |
| `/check_admin_compliance_v1` | POST | Admin-script policy v1 review |
| `/check_outline_compliance` / `/upload_outline_for_compliance` | POST | Outline compliance |
| `/batch_check_compliance` | POST | Batch compliance |
| `/export_compliance_report` / `/export_admin_compliance_review` | POST | Export report (DOCX/ODT) |
| `/check_quality` / `/batch_check_quality` | POST | Back-translation quality checks |

### Voice & Images

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/generate_voice` / `/generate_voice_combined` | POST | Per-slide / combined TTS |
| `/enhance_prompts` | POST | Visual cue → detailed image prompt |
| `/generate_images` / `/modify_image` | POST | Generate / edit images |
| `/upload_reference_image` | POST | Upload reference for image-to-image |

### Translation (`/translation`)

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/translation/languages` | GET | Supported languages |
| `/translation/translate` / `/translation/batch_translate` | POST | Translate to one / many languages |
| `/translation/export_docx` | POST | Export translation grid as DOCX |
| `/slides-translation/languages` | GET | Slide translation languages |
| `/translate_slides` | POST | Translate `.tex` file |

### Timed Script (`/timed-script`) — background jobs

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/timed-script/generate` | POST | Enqueue audio → Whisper transcription job |
| `/timed-script/jobs` | GET | List caller's jobs |
| `/timed-script/jobs/{job_id}` | GET | Poll one job |
| `/timed-script/download-docx` | POST | Result → DOCX |

### Script Chat (`/script-chat`)

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/script-chat/start` | POST | Create a thread, seed initial state |
| `/script-chat/stream/{thread_id}` | GET | SSE stream (progress/state/interrupt) |
| `/script-chat/resume/{thread_id}` | POST | Resume from a review interrupt (approve/edit) |
| `/script-chat/edit/{thread_id}` | PUT | Manual slide edit while paused |
| `/script-chat/history/{thread_id}` | GET | Full state snapshot |
| `/script-chat/threads` | GET | List caller's threads |
| `/script-chat/threads/{thread_id}/archive` | POST | Soft-archive |
| `/script-chat/checkpoints/{thread_id}` | GET | List version snapshots |
| `/script-chat/revert/{thread_id}` | POST | Revert to a checkpoint |
| `/script-chat/jump/{thread_id}` | POST | Jump to a stage |
| `/script-chat/export-docx/{thread_id}` | GET | Export current script as DOCX |
| `/script-chat/export-wiki/{thread_id}` | GET | Export current script as MediaWiki markup |

### Outline Chat & Redesign

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/outline_chat` / `/outline_chat_stream` | POST | Phased outline builder (+ SSE) |
| `/outline_chat/{project_id}/snapshot` | GET | Human-readable snapshot |
| `/outline_chat/{project_id}/edit` | POST | Edit a field |
| `/outline_chat/{project_id}/export` | GET | Export JSON/PDF |
| `/general_chat` | POST | General chat with web search |
| `/redesign/generate` | POST | Version Change Automation pipeline |
| `/redesign/share` | POST | Share generated Google Sheet |

### Downloads (`/download`)

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/download/outline/{filename}` | GET | Download outline file |
| `/download/image/{project_id}/{filename}` | GET | Download image |
| `/download/zip/{project_id}/{filename}` | GET | Download image ZIP |

---

## Frontend

React 19 + Vite 7 SPA in `chatbot-ui/`, styled with Tailwind CSS v4 and Radix-based (shadcn-style) UI primitives.

**Routes** (`src/App.jsx`):

| Path | Page | Protected |
|:-----|:-----|:---------:|
| `/`, `/login` | Login | Public |
| `/auth/callback` | OAuth callback handler | Public |
| `/create` | Create workflow (`Layout mode="create"`) | ✅ |
| `/outline-chat` | Outline Chat | ✅ |
| `/script-chat` | Script Chat (SSE) | ✅ |
| `/admin-compliance-review` | Admin compliance workspace | ✅ |

**Auth:** `AuthContext` stores the JWT (`auth_token` in `localStorage`), verifies it via `/auth/verify`, and handles the `?token=` OAuth callback. `ProtectedRoute` guards authenticated routes.

**Services:** `src/services/api.js` is the generic fetch wrapper (bearer injection, 401 → logout, 403 → domain error); `src/services/scriptChatService.js` drives the Script Chat SSE flow using authenticated `fetch` streaming.

**Production container** (`chatbot-ui/Dockerfile` + `nginx.conf`): multi-stage build — Node builds the bundle, `nginx:1.27-alpine` serves it and owns application routing: `/api/` → backend (300 s proxy timeouts — generation can run minutes), `/static/` and `/output/` → backend static mounts, `/grafana/` → Grafana, `/assets/` long-cached, everything else → SPA fallback.

**Scripts:** `npm run dev` · `npm run build` · `npm run preview` · `npm run lint`

---

## Deployment & CI/CD

Production runs on a Linux VPS (shared with two other organisation projects) as Docker Compose services behind a host nginx that terminates TLS (Let's Encrypt). **Images are never built on the server** — they are built in CI and pulled from the GitHub Container Registry.

![CI/CD pipeline](docs/diagrams/cicd-pipeline.svg)

<details>
<summary>Diagram source (Mermaid)</summary>

```mermaid
flowchart LR
    D([Push to main]) --> M["Build matrix<br/>backend · worker · frontend<br/>linux/amd64 · BuildKit cache"]
    M -->|push images| REG[("GHCR<br/>sha-&lt;commit&gt; + latest")]
    M -->|all 3 succeed| DEP["Deploy job<br/>SSH via gateway host"]
    DEP --> VM["VPS: scp compose.yaml + deploy/<br/>set IMAGE_TAG → pull → up -d<br/>restart grafana"]
    REG -.->|docker compose pull| VM
    VM --> H{"Health gate<br/>backend + worker<br/>up to 4 min"}
    H -->|healthy| OK([Deploy verified])
    H -->|unhealthy| FAIL["CI run fails<br/>+ last 50 log lines of each service"]
```

</details>

**Pipeline** (`.github/workflows/build.yml`, on push to `main`):

1. **Build** — a three-image matrix (`backend`, `worker`, `frontend`) builds in parallel on GitHub Actions (linux/amd64, BuildKit cache), and pushes to `ghcr.io/shagnik2704/slide-generator-{backend,worker,frontend}` tagged `sha-<commit>` (immutable) and `latest` (main only).
2. **Deploy** — gated on **all three** builds succeeding. SSHes to the VPS through a gateway host, copies `compose.yaml` + `deploy/` (configuration only — no source code reaches the server), writes `IMAGE_TAG=sha-<commit>` into `.env`, then `docker compose pull` + `up -d --remove-orphans`.
3. **Grafana restart** — datasource provisioning is read only at Grafana startup, so the deploy restarts Grafana unconditionally (non-fatal on failure).
4. **Health gate** — polls the backend health check (a live database round-trip) and the worker's Celery broker ping for up to 4 minutes. An unhealthy stack **fails the CI run** and dumps the last 50 log lines of each service.

**Rollback** (seconds, no rebuild):

```bash
# on the VPS
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=sha-<previous>/' .env && docker compose up -d
```

The server holds only `compose.yaml`, `deploy/` and `.env` — the `.env` file doubles as the record of what is deployed. Full operational detail (SSH topology, secrets inventory, procedures) is in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Monitoring

Everything is provisioned from files in this repository — a wiped Grafana volume fully self-heals.

- **Prometheus** (`deploy/prometheus.yml`) scrapes the backend `/metrics` every 15 s. The backend runs multiple uvicorn workers, so metrics use `prometheus_client` **multiprocess mode**: workers write to a shared `PROMETHEUS_MULTIPROC_DIR` on a tmpfs (recreated empty each start) and `/metrics` serves the aggregate — without this, scrapes hit whichever worker answers and counters read ~1000× too high.
- **Grafana 12** at `/grafana/` behind the frontend nginx. Two provisioned datasources (`deploy/grafana/provisioning/`): Prometheus, and PostgreSQL via the dedicated **read-only `grafana_ro` role** (SELECT-only — a mistaken dashboard query cannot modify data).
- **Dashboards as code** (`deploy/grafana/dashboards/app-overview.json`): request health and p95 latency (self-monitoring endpoints excluded), 5xx rate (deliberately including health-check 503s — they signal database outages), per-user activity, job runtimes, and where script threads stall by stage.
- **LangSmith** traces every LangChain/LangGraph LLM call (zero code — env vars only) into the `slide-generator` project, with per-node token/cost attribution (~$0.05 per script end-to-end).

---

## Development

```bash
# Backend
uv sync                              # install deps
uv run python -m src.script_chat.migrate   # apply migrations
uv run python -m src.api             # run API
uv run pytest                        # run tests (tests/ — 22 modules, Postgres-backed tests need the DB up)

# Create a new migration (hand-written; migrations are not autogenerated)
uv run alembic -c alembic.ini revision -m "description"

# Frontend
cd chatbot-ui
npm run dev
npm run build
npm run lint
```

Code conventions (layering, imports, docstrings, error handling, naming) are documented in [`docs/.code-structure.md`](docs/.code-structure.md).

---

## Project Structure

```
slide-generator/
├── src/
│   ├── api/
│   │   ├── server.py            # FastAPI app: 15 routers, middleware, lifespan, Prometheus
│   │   ├── config.py            # Pydantic settings (env validation)
│   │   ├── auth.py / auth/      # JWT + Google OAuth
│   │   ├── middleware.py        # Security headers + request logging
│   │   └── routes/              # route modules (+ outline_chat/ with 14 submodules)
│   ├── script_chat/             # Script Chat: LangGraph graph, nodes, prompts,
│   │   │                        #   persistence.py (shared pool), migrate.py, routes.py
│   │   └── nodes/               # ingest, ground, metadata, generate, edit, compliance…
│   ├── compliance/              # Admin-script compliance: policies, validators, report
│   ├── jobs/                    # Background-job persistence (background_jobs table)
│   ├── workers/                 # Celery app + tasks (Whisper transcription)
│   ├── users/                   # User identity persistence (users table)
│   ├── core/                    # Core script-gen LangGraph (agent.py, state.py)
│   ├── nodes/                   # Script-gen + Version Change pipeline nodes
│   ├── services/                # Business logic (voice, image, docx, pdf, latex, translation…)
│   ├── utils/                   # LLM init, audio/pdf helpers
│   └── workflow.py              # Version Change Automation runner
├── migrations/                  # Alembic migrations (threads, users, background_jobs)
├── alembic.ini
├── chatbot-ui/                  # React 19 + Vite 7 frontend + its Dockerfile + nginx.conf
├── docker/
│   ├── backend.Dockerfile       # API image (uv multi-stage, Python 3.11 + FFmpeg, no Whisper)
│   └── worker.Dockerfile        # Whisper worker image (bakes the base model at build time)
├── deploy/
│   ├── prometheus.yml           # Scrape config
│   └── grafana/                 # Provisioned datasources + dashboards (as code)
├── compose.yaml                 # Single source of truth for all 8 services
├── compose.override.yaml        # Dev-only, LOCAL-ONLY (gitignored): adds build: stanzas
├── docs/                        # HLD, deployment runbook, diagrams/, code conventions
├── tests/                       # pytest suite (22 modules)
└── .github/workflows/build.yml  # CI/CD: build matrix → GHCR → health-gated deploy
```

---

## Further Documentation

- [`docs/HLD.md`](docs/HLD.md) — high-level design: system overview, pipelines, data model, integrations, deployment topology.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — operations runbook: server layout, deploy/rollback procedures, secrets inventory, monitoring access, known follow-ups.
- [`docs/.code-structure.md`](docs/.code-structure.md) — code conventions.

## License

MIT
