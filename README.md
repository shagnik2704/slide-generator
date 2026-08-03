# Spoken Tutorial Generator

AI-powered platform for producing [Spoken Tutorial](https://spoken-tutorial.org/) content — outlines, scripts, slides, voice narration, images, and translations — from a simple course outline. Built for the Spoken Tutorial Project at IIT Bombay.

**Live:** [spokenai.live](https://spokenai.live)

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
- [Deployment](#deployment)
- [Development](#development)
- [Project Structure](#project-structure)

---

## Overview

The Spoken Tutorial Generator is a full-stack application (FastAPI backend + React frontend) that automates the Spoken Tutorial content-authoring pipeline. It combines several LLM-driven workflows — outline interviews, script generation, compliance review, translation, and voice/image/slide generation — behind a single chat-style UI.

The backend has recently moved from a single-process SQLite setup to a **PostgreSQL-backed, horizontally-scalable architecture**:

- **PostgreSQL** stores users, chat threads, background-job records, and LangGraph checkpoints.
- **Celery + Redis** run long/heavy tasks (Whisper transcription) out-of-band from the API.
- **Alembic** manages the relational schema; LangGraph's `AsyncPostgresSaver` manages checkpoint tables.
- A dedicated **Whisper worker container** isolates the heavy speech-to-text dependency from the API image.

---

## Features

| Feature | Description |
|:--------|:------------|
| **Script Chat** | Conversational, human-in-the-loop script authoring via a LangGraph state machine (ingest → grounding → metadata → generation → editing → compliance). Streams progress over SSE, pauses at review gates, supports manual edits, checkpoint/version history, revert, and stage jumps. Persisted per-user in PostgreSQL. |
| **Outline Chat** | Phased SME interview (warmup → outcomes → examples → structure → metadata → review) that builds a Spoken Tutorial course outline, with streaming SSE, field editing, validation, and PDF/JSON export. |
| **Script Generation** | LangGraph pipeline (metadata → boilerplate → content → merge → evaluator loop) that turns an outline into a structured JSON script. |
| **Slides Generation** | Beamer LaTeX slides, auto-populated from scripts via LLM content extraction. |
| **Voice Generation** | Google Gemini TTS — per-slide audio (ZIP) or a single combined tutorial audio. |
| **Image Generation** | AI-enhanced prompts → image generation, with prompt-review UI, reference-image upload, and per-image editing. |
| **Compliance** | Evidence-based admin-script compliance (`admin_script_v1` policy, 25 criteria) combining deterministic validators with LLM semantic + factuality checks, plus an admin review workspace. Pedagogy/quality compliance via back-translation. |
| **Translation** | Multi-language batch translation with an editable translation grid, per-cell TTS, and DOCX export. |
| **Slides Translation** | Translate `.tex` Beamer files to 11+ Indian languages with XeLaTeX Unicode support. |
| **Timed Script** | Upload audio/video → **background** Whisper transcription → sentence-level timestamps → DOCX export. |
| **MediaWiki Export** | One-click export to Spoken Tutorial wiki table format (from JSON or DOCX). |
| **Version Change Automation** | Scrapes spoken-tutorial.org → LLM + Tavily web search for version updates → splits long tutorials into 3–4 min fragments → tabulates old-vs-new comparison → exports to Google Sheets via Workload Identity Federation. |
| **Google OAuth** | Domain-restricted Google authentication issuing JWTs; stable per-user identity in PostgreSQL. |

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     Frontend — React 19 + Vite 7 (Nginx)                    │
│  Pages: Create · Outline Chat · Script Chat · Admin Compliance Review       │
│  Auth: Google OAuth → JWT (bearer, localStorage) · SSE streaming            │
└───────────────────────────────────────────────────────────────────────────┘
                         │ HTTPS  (/api reverse proxy)
                         ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Backend API — FastAPI (uvicorn, 4 workers)               │
│  15 routers · Prometheus /metrics · security + CORS middleware              │
│  LangGraph graphs:  core script pipeline  +  Script Chat (checkpointed)     │
│  Enqueues heavy work to Celery; never runs Whisper in-process               │
└───────────────────────────────────────────────────────────────────────────┘
        │ send_task                    │ SQL (asyncpg/psycopg pool)
        ▼                              ▼
┌──────────────────────┐   ┌──────────────────────────────────────────────┐
│  Redis (Celery broker)│   │            PostgreSQL 16                      │
└──────────┬───────────┘   │  users · script_chat_threads ·               │
           │ consume        │  background_jobs   (Alembic-managed)          │
           ▼                │  checkpoints…      (LangGraph-managed)        │
┌──────────────────────┐   └──────────────────────────────────────────────┘
│  Whisper worker       │
│  (Celery, queue=whisper)│  speech-to-text → writes result to background_jobs
└──────────────────────┘
                         │
                         ▼
   External AI / services:  Google Gemini (text · TTS · image) ·
   OpenAI (semantic compliance) · Tavily (web search) · Sarvam (TTS) ·
   OpenAI Whisper (local, base model) · Google Sheets (WIF)
```

Key points:

- A **single shared PostgreSQL connection pool** lives in `src/script_chat/persistence.py`; the `jobs` and `users` modules import it rather than opening their own.
- The **API image contains no Whisper/torch** — those live only in `Dockerfile.whisper-worker`.
- **Redis is only the Celery broker** (no result backend); job results are stored in the `background_jobs.result` JSONB column.

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic v2, uvicorn |
| Async jobs | Celery 5, Redis 7 |
| Database | PostgreSQL 16, psycopg 3 (pooled), SQLAlchemy + Alembic (migrations), LangGraph `AsyncPostgresSaver` (checkpoints) |
| Frontend | React 19, Vite 7, React Router 6, Tailwind CSS v4, Radix UI (shadcn-style), `motion`, lucide-react, react-markdown |
| AI / LLM | Google Gemini (text, TTS, image), OpenAI (semantic compliance, `gpt-5.2`), Sarvam (TTS) |
| Search | Tavily API |
| Speech-to-text | OpenAI Whisper (local, `base` model) |
| PDF / Slides | LaTeX (Beamer / XeLaTeX), python-docx, ReportLab, PyMuPDF, pdfplumber |
| Video / Audio | FFmpeg, MoviePy, pydub |
| Auth | Google OAuth 2.0, python-jose (JWT) |
| Infra | Docker Compose, Nginx (SSL), GitHub Actions CI/CD (WIF + SSH), Prometheus |
| Package mgmt | uv (Python), npm (JS) |

---

## Quick Start

### Prerequisites

- **Python 3.11** (project supports `>=3.10,<3.13`) via [uv](https://github.com/astral-sh/uv): `curl -Ls https://astral.sh/uv/install.sh | sh`
- **Node.js 20+**
- **PostgreSQL 16** and **Redis 7** (or use the Docker Compose services below)
- **LaTeX** for PDF/slide generation: `brew install --cask mactex-no-gui` (macOS) or `apt install texlive-full texlive-xetex` (Linux)
- **FFmpeg** for audio/video: `brew install ffmpeg` or `apt install ffmpeg`

### Option A — Docker Compose (recommended)

The committed `docker-compose.postgres.yml` brings up Postgres, Redis, runs migrations, and starts the API + Whisper worker:

```bash
# 1. Create a .env file at the project root (see Configuration below)

# 2. Bring up the data services, run migrations, start API + worker
docker compose -f docker-compose.postgres.yml up --build -d
```

The `migrate` service runs `python -m src.script_chat.migrate` (Alembic + LangGraph checkpoint setup) and must complete before the backend and worker start — this is wired via `depends_on`.

### Option B — Local processes

```bash
# --- Data services (if not already running) ---
docker compose -f docker-compose.postgres.yml up -d postgres redis

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

Configuration is read from environment variables (loaded from a `.env` file at the project root). Backend settings are validated in `src/api/config.py`.

### Core

| Variable | Default | Description |
|:---------|:--------|:------------|
| `ENVIRONMENT` | `development` | `development` or `production` (enables stricter validation; disables `/docs` in prod) |
| `DEBUG` | `false` | Enables request logging middleware |
| `DATABASE_URL` | `postgresql://spoken_tutorial:spoken_tutorial@localhost:5432/spoken_tutorial` | PostgreSQL DSN (used for app tables **and** LangGraph checkpoints) |
| `DATABASE_POOL_MIN_SIZE` / `DATABASE_POOL_MAX_SIZE` | `1` / `5` | Connection pool bounds |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `10` | Pool checkout timeout |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker for background jobs |
| `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS` | `1800` | A timed-script job still `running` past this is treated as stuck and marked `failed` by the stale-job reaper. Set comfortably above the slowest transcription. |
| `TIMED_SCRIPT_REAPER_INTERVAL_SECONDS` | `300` | How often a `celery beat` process runs the stale-job reaper. The worker also reaps opportunistically on every job, so `beat` is optional. |

### Auth

| Variable | Description |
|:---------|:------------|
| `JWT_SECRET_KEY` | **Required.** Must be ≥32 chars in production |
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
| `GOOGLE_API_KEY` | Gemini text, TTS, and image generation |
| `OPENAI_API_KEY` | Semantic + factuality compliance checks (skipped if unset) |
| `TAVILY_API_KEY` | Web search (outline chat, version-change pipeline) |
| `SARVAM_API_KEY` | Sarvam TTS voices |
| `SARVAM_PRONUNCIATION_DICT_ID` | Optional. Id of a Sarvam pronunciation dictionary (branding/jargon fixes) applied to every TTS request. TTS runs without correction if unset. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Sheets export (Version Change Automation) via Workload Identity Federation |

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
- **Queue routing:** the timed-script task is routed to the `whisper` queue; the Whisper worker container consumes only that queue with `--concurrency=1` / `worker_prefetch_multiplier=1` (one heavy job at a time).
- **Crash recovery:** with `task_acks_late` + `task_reject_on_worker_lost`, a worker that dies mid-transcription has its task redelivered. The task is bound (`self.request.id`), so `claim_job` can re-claim its own `running` row on redelivery instead of leaving it stuck forever; the input file survives because it is deleted only on a terminal state. As a backstop, a **stale-job reaper** fails jobs that have been `running` past `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS` (run opportunistically on every job and, optionally, on a `celery beat` schedule) so the polling UI always terminates.

Celery config lives in `src/workers/celery_app.py`; job persistence in `src/jobs/persistence.py`.

> Timed Script is currently the only background-job type. Translation and other endpoints remain synchronous.

---

## Key Workflows

### Script Chat (`src/script_chat/`)

A checkpointed LangGraph state machine for conversational, human-in-the-loop script authoring:

```
START → ingest → ground → ground_review ⇄ ground_edit
                        → metadata → metadata_review ⇄ metadata_edit
                        → generate → script_review ⇄ edit
                        → compliance → compliance_review → END
```

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

```
Outline → metadata_node → boilerplate_node → content_node → merge_node → Evaluator
                                                                  ↓ pass → Final JSON script
                                                                  ↓ fail → loop back with feedback
```

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
| `/metrics` | GET | Prometheus metrics |

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

**Scripts:** `npm run dev` · `npm run build` · `npm run preview` · `npm run lint`

---

## Deployment

Production runs on a GCP VM via Docker Compose behind Nginx (SSL). CI/CD is GitHub Actions (`.github/workflows/deploy.yml`):

1. Push to `main` triggers the workflow.
2. GitHub Actions authenticates to GCP via **Workload Identity Federation** (keyless).
3. It SSHes into the VM, pulls, and runs `docker compose up --build -d`.

Containers:

- **backend** — FastAPI (uvicorn, 4 workers) on `:8000`, health-checked at `/health`.
- **whisper-worker** — Celery worker consuming the `whisper` queue (built from `Dockerfile.whisper-worker`, bakes the Whisper `base` model into the image).
- **migrate** — one-shot `python -m src.script_chat.migrate`, gates backend/worker startup.
- **postgres** (16) and **redis** (7) — data services with health checks and named volumes.
- **frontend** — Nginx serving the built React app + reverse-proxying `/api` to the backend (see `chatbot-ui/Dockerfile`).

SSL certificates are managed with Let's Encrypt (certbot) on the host and mounted into Nginx. Prometheus scrape config is in `prometheus.yml`; the API exposes `/metrics`.

> The repo commits `docker-compose.postgres.yml` (Postgres + Redis + migrate + backend + worker). The host-specific `docker-compose.yml` (backend + frontend + certs, gitignored) is provisioned per-environment.

---

## Development

```bash
# Backend
uv sync                              # install deps
uv run python -m src.script_chat.migrate   # apply migrations
uv run python -m src.api             # run API
uv run pytest                        # run tests (tests/)

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
│   │   ├── server.py            # FastAPI app: routers, middleware, lifespan, Prometheus
│   │   ├── config.py            # Pydantic settings (env validation)
│   │   ├── auth.py / auth/      # JWT + Google OAuth
│   │   ├── middleware.py        # Security headers + request logging
│   │   └── routes/              # 14 route modules (+ outline_chat/ with 14 submodules)
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
├── migrations/                  # Alembic migrations (users, threads, background_jobs)
├── alembic.ini
├── chatbot-ui/                  # React 19 + Vite 7 frontend
├── docs/                        # Design notes, code structure, sample docs
├── tests/                       # pytest suite
├── Dockerfile                   # Backend/API image (Python + FFmpeg, no Whisper)
├── Dockerfile.whisper-worker    # Whisper worker image (adds openai-whisper + base model)
├── docker-compose.postgres.yml  # Postgres + Redis + migrate + backend + worker
├── prometheus.yml               # Monitoring scrape config
└── .github/workflows/deploy.yml # CI/CD (WIF + SSH deploy)
```

---

## License

MIT
