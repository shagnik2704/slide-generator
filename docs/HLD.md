# High-Level Design — Spoken Tutorial Generator

> Generated from a direct read of the codebase (routers, LangGraph graphs, migrations,
> `compose.yaml`, Dockerfiles, CI workflow) rather than from `README.md` alone.
> Last verified against the code on 2026-08-11 (commit `8458377`). Operational
> procedures (deploy, rollback, recovery) live in [DEPLOYMENT.md](DEPLOYMENT.md).

## 1. Purpose & scope

A full-stack platform that turns a course outline into Spoken Tutorial content — scripts,
slides, voice narration, images, translations, and compliance review — through a set of
LLM-driven, mostly chat-style workflows. Built for the Spoken Tutorial Project (IIT Bombay);
production at [creation.edupyramids.org](https://creation.edupyramids.org), restricted to
`@edupyramids.org` accounts. (The domain lives only in the server's `.env` and the host
nginx config — nothing in this repo hardcodes it.)

## 2. System overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend — React 19 SPA, served by Nginx                                │
│  Pages: Create · Outline Chat · Script Chat · Admin Compliance Review     │
│  Auth: Google OAuth → JWT (bearer, localStorage) · SSE for streaming      │
└─────────────────────────────────────────────────────────────────────────┘
                    │ /api  (nginx reverse proxy, in-container)
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Backend API — FastAPI (uvicorn, 4 workers)                              │
│  15 routers · Prometheus /metrics · security + CORS middleware           │
│  Two LangGraph graphs: core script-gen (stateless) + Script Chat         │
│  (Postgres-checkpointed, human-in-the-loop). Enqueues Whisper work only. │
└─────────────────────────────────────────────────────────────────────────┘
      │ send_task                              │ SQL (psycopg pool)
      ▼                                         ▼
┌───────────────────────┐         ┌─────────────────────────────────────┐
│ Redis — Celery broker  │         │  PostgreSQL 16                       │
│ (no result backend)    │         │  users · script_chat_threads ·      │
└──────────┬─────────────┘         │  background_jobs  (Alembic)         │
           │ consume               │  checkpoints…     (LangGraph)       │
           ▼                       └─────────────────────────────────────┘
┌───────────────────────┐
│ Whisper worker         │  Celery, queue=whisper, concurrency=1
│ (own container/image)  │  speech-to-text → writes to background_jobs
└───────────────────────┘

External:  Google Gemini (text + image) · OpenAI (semantic compliance) ·
           Sarvam (TTS) · Tavily (web search) · local Whisper (base model) ·
           Google Sheets via Workload Identity Federation (redesign export)

Observability:  Prometheus (15s scrape, multiprocess-aggregated /metrics) ·
           Grafana 12 (datasources + 30-panel dashboard provisioned from
           deploy/grafana/ in git; read-only grafana_ro Postgres role) ·
           LangSmith tracing (LangChain-based calls, project "slide-generator")
```

Rendered, theme-aware versions of this and the other diagrams live in
[`diagrams/`](diagrams/) (production architecture, CI/CD pipeline, and the
Script Chat state machine) and are embedded in the README.

## 3. Frontend

React 19 + Vite 7 SPA in `chatbot-ui/`, Tailwind CSS v4, Radix primitives
(alert-dialog, select, tabs, tooltip, scroll-area — shadcn-style), `lucide-react`
icons, `motion` for animation, `react-markdown`. No state-management library —
state is composed from custom hooks (`useChatArea` fans out to per-feature
handler hooks) plus `localStorage` persistence (`src/utils/chatStorage.js`).

**Routes** (`src/App.jsx`):

| Path | Page | Protected |
|---|---|---|
| `/`, `/login` | Login | Public |
| `/auth/callback` | OAuth callback | Public |
| `/create` | Create workflow (chat-style tool launcher) | ✅ |
| `/outline-chat` | Outline Chat | ✅ |
| `/script-chat` | Script Chat (SSE) | ✅ |
| `/admin-compliance-review` | Admin compliance workspace | ✅ |

**Auth:** `AuthContext` holds the JWT (`auth_token` in `localStorage`), verifies it
against `/auth/verify` on load, and consumes the `?token=` OAuth callback.
`ProtectedRoute` redirects unauthenticated users to `/login`.

**API layer:** `src/services/api.js` — generic fetch wrapper, bearer injection,
401 → logout, 403 → domain-restriction error. `scriptChatService.js` drives the
Script Chat SSE stream over authenticated `fetch`. In dev, Vite proxies `/api`
and `/output` to `localhost:8000` (`vite.config.js`); in the container, Nginx
does the equivalent (§8).

## 4. Backend API

FastAPI app (`src/api/server.py`), 15 routers registered at startup:

`auth · upload · compliance · quality · voice · images · slides · generation ·
download · outline_chat · translation · redesign · timed_script ·
slides_translation · script_chat`

Cross-cutting: `SecurityHeadersMiddleware` always on; `LoggingMiddleware` only in
dev/debug; CORS from `CORS_ORIGINS`; `prometheus_fastapi_instrumentator` exposes
`/metrics`; `/docs`/`/redoc`/`/openapi.json` are disabled outside development.
`/health` checks the Script Chat Postgres pool and returns 503 if it's down.
Two directories are mounted as static file servers: `/static` and `/output`.

Full endpoint-by-endpoint reference is in `README.md § API Reference` — verified
accurate against the router list above.

### 4.1 Two LangGraph pipelines

**(a) Core script-generation graph** (`src/core/agent.py`) — stateless, no
checkpointer by default:

```
START → extract_metadata ──┬──→ generate_boilerplate ──┐
                            └──→ generate_content ──────┴──→ merge_script → END
```

4 nodes, one parallel fan-out/fan-in. `extract_metadata` produces `ScriptMetadata`;
`generate_boilerplate` and `generate_content` run **concurrently** off that
metadata; `merge_script` combines everything into the final `json_script`.
**There is no evaluator/retry loop in the active graph** — an `evaluator_node.py`
exists but lives under `src/nodes/_archive/` and is not wired into `build_graph()`.

**(b) Script Chat graph** (`src/script_chat/graph.py`) — human-in-the-loop,
checkpointed with `AsyncPostgresSaver` so it survives restarts and supports
revert/version history:

```
START → ingest → ground → ground_review ⇄ ground_edit
                        → metadata → metadata_review ⇄ metadata_edit
                        → generate → script_review ⇄ edit
                        → compliance → compliance_review → END
```

Each `*_review` stage is a LangGraph `interrupt()` — the graph pauses, the
client resumes it via `POST /script-chat/resume/{thread_id}` with `approve` or
`edit`. `generate` and `edit` call the OpenAI Responses API directly (not
`ChatOpenAI`) so they can use the `web_search_preview` tool; every other LLM
call goes through `langchain_openai.ChatOpenAI`. One script = one `thread_id`,
spanning many short-lived graph invocations (one per HTTP request/resume).

### 4.2 Background jobs (Celery + Redis)

Timed Script is the **only** background-job type today; everything else
(translation, voice, images, compliance) runs synchronously in the request.

- **Enqueue:** `POST /timed-script/generate` streams the upload to disk, inserts
  a `background_jobs` row, then `celery_app.send_task(...)`.
- **Worker:** `src/workers/tasks.py::process_timed_script` claims the job
  (`queued→running`, idempotent against duplicate delivery), transcribes with
  Whisper, writes `completed`/`failed`. Routed to the dedicated `whisper` queue,
  consumed with `--concurrency=1` so only one heavy transcription runs at a time.
- **Crash recovery:** `task_acks_late` + `task_reject_on_worker_lost` redeliver a
  task if its worker dies mid-job; a **stale-job reaper**
  (`reap_stale_timed_script_jobs`, opportunistic on every job + optional
  `celery beat` schedule) fails anything stuck `running` past
  `TIMED_SCRIPT_JOB_TIMEOUT_SECONDS` (default 1800s) so polling clients always
  terminate.
- **Result storage:** Redis is the broker only (no result backend) — results
  live in `background_jobs.result` (JSONB).

### 4.3 Compliance subsystem (`src/compliance/`)

`workflow.py::run_admin_script_compliance` orchestrates:

1. `validators/deterministic.py` — two-column format, required metadata,
   section presence, duration bounds, sentence-length limits, live link checks.
2. `validators/semantic.py` — LLM checks (structure/flow, visual-demo alignment,
   terminology, a two-stage web-search-backed factuality pass); silently
   skipped if `OPENAI_API_KEY` is unset.
3. `report.py` merges both into a structured `ComplianceReport` with per-row
   annotations, scored against `policies/admin_script_v1.py` (25 criteria).

Notably, `build_script_artifact` reads a slide's visual cue from **either**
`image_prompt` or `visual_cue` — the same current-vs-legacy script-shape split
that recurs across the codebase (compliance, MediaWiki export, DOCX export).
Invoked by both the standalone compliance router and the Script Chat
`compliance` node.

### 4.4 Service layer (`src/services/`)

| File | Purpose |
|---|---|
| `beamer_service.py` | Builds the Beamer `.tex` template (boilerplate slides, theme colour) |
| `content_extractor.py` | LLM extraction that fills the Beamer template from a script |
| `mediawiki_service.py` | JSON script → MediaWiki table markup (Spoken Tutorial wiki) |
| `docx_service.py` | Script ↔ `.docx` (export + parse-back), the DOCX-upload entry point |
| `outline_docx_service.py` / `outline_pdf_service.py` | Course-outline export |
| `outline_service.py` | Markdown → Word doc utilities for outlines |
| `pdf_service.py` / `latex_service.py` | Legacy PDF/slide rendering path |
| `voice_service.py` | TTS — **Sarvam** (`api.sarvam.ai/text-to-speech`), per-slide or combined |
| `image_service.py` | Image generation — Google `genai` client, `gemini-3-pro-image-preview` |
| `image_styles.py` / `prompt_enhancer.py` | Shared style guide + visual-cue → image-prompt enhancement (Gemini 2.5 Flash) |
| `quality_service.py` | Back-translation pedagogy/quality check |
| `compliance_service.py` | Non-admin-policy compliance checking |
| `translation_service.py` | Multi-language script translation |
| `slides_translation_service.py` | Translate `.tex` Beamer files (11+ Indian languages, XeLaTeX) |
| `timed_script_service.py` | Whisper transcription → sentence-level timestamps |

## 5. Data model

PostgreSQL 16, one shared connection pool (`src/script_chat/persistence.py`),
reused by the `jobs` and `users` modules rather than each opening its own.

| Table | Owner | Key columns |
|---|---|---|
| `users` | Alembic `20260711_02` | `id` (UUID PK), `provider` + `provider_subject` (unique pair), `email` (unique), `name`, `picture`, `last_login_at`. JWT `sub` = this UUID. |
| `script_chat_threads` | Alembic `20260710_01`/`_02` | `thread_id` (PK), `user_id` (FK → users, `RESTRICT`), `title`, `outline_preview`, `foss_name`, `current_stage`, `status` (`created/running/awaiting_review/completed/failed`), `archived_at` (soft delete). |
| `background_jobs` | Alembic `20260711_03` | `id` (UUID PK), `user_id` (FK), `job_type`, `status` (`queued/running/completed/failed`), `celery_task_id`, `input_path`, `result` (JSONB), `progress` (0–100), `current_stage`, timestamps. |
| `checkpoints`, … | LangGraph `AsyncPostgresSaver.setup()` | Script Chat conversation state + version history. Created by `python -m src.script_chat.migrate`, **not** Alembic. |

Migrations are hand-written (not autogenerated) and applied by
`python -m src.script_chat.migrate`, which runs `alembic upgrade head` and then
sets up the LangGraph checkpoint tables — this must complete before the API or
worker start (`migrate` service gates them in `compose.yaml`).

## 6. External integrations

| Concern | Provider | Notes |
|---|---|---|
| Text generation | OpenAI (`gpt-5.4-mini`, `gpt-5.2`, `gpt-5-nano`) via `langchain_openai` / raw Responses API | Script Chat, compliance semantic checks |
| Text generation (secondary) | Google Gemini (`gemini-2.5-flash`) | Prompt enhancement, some core-pipeline nodes |
| Image generation | Google Gemini (`gemini-3-pro-image-preview`) via `google.genai` | |
| Text-to-speech | **Sarvam** (`api.sarvam.ai`) | Actual code path — see [§9](#9-known-drift-from-readmemd) |
| Web search | Tavily | Outline chat, factuality checks, version-change automation |
| Speech-to-text | OpenAI Whisper, `base` model, local (no API) | Runs only in the dedicated worker container |
| Auth | Google OAuth 2.0 → JWT (`python-jose`), domain-restricted (`ALLOWED_EMAIL_DOMAIN`, default `@edupyramids.org`) | |
| Sheets export | Google Sheets via Workload Identity Federation | Only for the Version Change Automation feature — **not** used for the GCP VM deploy itself |
| Tracing | LangSmith (`LANGSMITH_TRACING`, project `slide-generator`) | Wraps LangChain calls app-wide; used this session to build a per-script cost report |

Config validation lives in `src/api/config.py` (Pydantic `Settings`) — enforces
a real `JWT_SECRET_KEY` (≥32 chars) in production, parses `CORS_ORIGINS`, and
sizes the DB pool (`DATABASE_POOL_MIN_SIZE`/`MAX_SIZE`/`TIMEOUT_SECONDS`).

### 6.1 LangSmith tracing & LLM cost observability

Verified against the live LangSmith project (read-only API), not just config.

**Zero-code instrumentation.** There is no `langsmith` import, `@traceable`
decorator, or `wrap_openai` call anywhere in `src/` — tracing is enabled
entirely through environment variables (`LANGSMITH_TRACING`,
`LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT` — the APAC region endpoint —
and `LANGCHAIN_PROJECT=slide-generator`). LangChain and LangGraph pick these
up and auto-emit traces; instrumenting a new workflow costs nothing as long
as it goes through LangChain.

**One project, feature attribution via metadata.** All features share the
single `slide-generator` project. Traces are attributed to features through
run metadata rather than separate projects: `thread_id` (which Script Chat
conversation), `langgraph_node` (which graph node), `ls_model_name`/
`ls_provider` (which model). One script = one `thread_id` spanning many
traces, because each human-in-the-loop resume is a separate graph invocation;
LangSmith's Threads view reassembles them.

**Three LangGraph workflows observed emitting traces in production data:**

1. **Script Chat** — every node (`ingest`, `ground`, `metadata`, `generate`,
   `edit`, `compliance`, …) with per-node token/cost. The `generate`/`edit`
   nodes call the OpenAI Responses API rather than `ChatOpenAI`, and still
   appear with full token and cost capture.
2. **Core script-gen pipeline** (`/generate_script`).
3. **Tutorial Redesign / Version Change** (`src/nodes/redesign/`) — its
   `create_react_agent` update-search agent and the `planning_agent` ⇄
   `reasoning_agent` critique loop from `split.py` show up as graph nodes.

Plus non-graph LangChain chains (translation, quality back-translation, the
compliance semantic validators) appearing as `RunnableSequence`/`ChatOpenAI`
root runs.

**Cost accounting works end-to-end.** In sampled 30-day windows, 100% of LLM
runs carried token counts and 100% carried a computed `total_cost` (per-model
prices are configured in LangSmith's model price map). This enables
per-script cost reporting by grouping LLM leaf runs on `thread_id` — measured
at roughly **$0.05 per script end-to-end** (generation ~38%, grounding ~28%,
editing ~22%, compliance ~8%), with a sessions-started vs scripts-completed
funnel as a byproduct.

**Coverage boundaries — what LangSmith does *not* see:** image generation
(raw `google.genai` client), Sarvam TTS (raw `httpx`), and Whisper
transcription (local model, not an LLM API) bypass LangChain and emit no
traces. LangSmith therefore reports **LLM text costs only**, not the full
per-tutorial COGS — image/TTS spend must come from those providers' own
dashboards.

## 7. Recent additions (July–August 2026)

- **MediaWiki export** now reads both script shapes (current `script`/`visual_cue`
  and legacy `slides`/`image_prompt`), preserves boilerplate-slide content
  (Acknowledgement names, Disclaimer/Thank-You sentences) instead of collapsing
  to a bare label, and always shows the EduPyramids link on the Pre-requisites
  slide. Script Chat gained its own `GET /script-chat/export-wiki/{thread_id}`.
- **Slide theme colour**: `generate_beamer_template` takes a validated
  `theme_color` (hex, rejected otherwise — it lands in a compiled `.tex`);
  the slides workflow card lets the user pick a palette colour or custom hex
  before generating, persisted in `localStorage`.

## 8. Deployment & CI/CD

Production runs on a GCP VM via Docker Compose behind Nginx. **This differs
from what `README.md` currently describes** — see [§9](#9-known-drift-from-readmemd).

**CI** (`.github/workflows/build.yml`, triggers on push to `main` or
`rewrite/infra`):

1. Builds three images via Buildx — `backend` (`docker/backend.Dockerfile`),
   `worker` (`docker/worker.Dockerfile`), `frontend` (`chatbot-ui/Dockerfile`) —
   and pushes each to `ghcr.io/<repo>-{backend,worker,frontend}`, tagged both
   `sha-<short>` and `latest` (on `main`).
2. **Deploy job** (only on `main`, gated on all three builds succeeding): SCPs
   `compose.yaml` + the whole `deploy/` directory (Prometheus config, Grafana
   datasource/dashboard provisioning) to the VM through a bastion/gateway host
   (`appleboy/scp-action` + `appleboy/ssh-action`, plain SSH keys — not
   Workload Identity Federation), pins `IMAGE_TAG` to the new sha in `.env`,
   then `docker compose pull` + `docker compose up -d --remove-orphans`.
3. **Restarts Grafana unconditionally** (non-fatal): datasource provisioning
   is read only at Grafana startup, and `up -d` won't recreate the container
   when only a mounted file changed.
4. **Health gate:** polls the backend healthcheck (HTTP `/health`, a live DB
   round-trip) and the whisper-worker's Celery broker ping for up to
   4 minutes; an unhealthy stack fails the CI run and dumps the last 50 log
   lines of each service.

**Rollback:** every merge's images remain in GHCR under their immutable
`sha-` tag; `.env` on the VM records the deployed tag. Rollback = point
`IMAGE_TAG` at a previous sha and `docker compose up -d` — seconds, no
rebuild (procedure in [DEPLOYMENT.md](DEPLOYMENT.md)).

**`compose.yaml` services:**

| Service | Image | Role |
|---|---|---|
| `postgres` | `postgres:16-alpine` | App DB + LangGraph checkpoints |
| `redis` | `redis:7-alpine` | Celery broker only |
| `migrate` | `ghcr.io/…-backend` | One-shot Alembic + checkpoint setup, gates `backend`/`whisper-worker` |
| `backend` | `ghcr.io/…-backend` | FastAPI, healthchecked at `/health` |
| `whisper-worker` | `ghcr.io/…-worker` | Celery worker, `whisper` queue only |
| `frontend` | `ghcr.io/…-frontend` | Nginx + built React app, on `127.0.0.1:8080` |
| `prometheus` | `prom/prometheus:v3.1.0` | Scrapes backend `/metrics` |
| `grafana` | `grafana/grafana:12.3.2` | Dashboards, served at `/grafana/` sub-path |

**Images:** `docker/backend.Dockerfile` is a `uv`-managed multi-stage Python
3.11 build (+ ffmpeg, no Whisper/torch). `docker/worker.Dockerfile` adds the
`whisper-worker` extra and **bakes the Whisper `base` model in at build time**.
`chatbot-ui/Dockerfile` builds the Vite app then serves it from `nginx:1.27-alpine`.

**Nginx** (`chatbot-ui/nginx.conf`) proxies `/api/` → `backend:8000` (300s
timeouts — generation can run minutes; nginx's default is 60s), `/static/` and
`/output/` → the backend's mounted static dirs, `/grafana/` → `grafana:3000`,
long-caches `/assets/`, and falls through everything else to the SPA
(`try_files … /index.html`).

## 9. README alignment

An earlier revision of this section catalogued seven points where `README.md`
had fallen behind the infrastructure rewrite (stale compose filename, VM-side
builds, WIF-based deploys, wrong TTS provider, a phantom evaluator loop,
old Dockerfile paths). The README was rewritten on **2026-08-11** to match the
code, and all seven were fixed — if the two documents disagree again, trust
the code, then this HLD, then the README, and re-align whichever is behind.

## 10. Notable design choices

- **One shared Postgres pool** for all app-owned tables (not just Script Chat),
  to avoid each subsystem managing its own connections.
- **API image ships no ML weights.** Whisper/torch live only in the worker
  image, keeping the main API image small and its cold-start fast.
- **Dual script-shape tolerance** is a recurring pattern (compliance,
  MediaWiki export, DOCX round-trip) — the codebase has evolved through at
  least two script JSON shapes (`slides`/`image_prompt` vs `script`/`visual_cue`)
  and several services deliberately support both rather than migrating all
  callers at once.
- **Synchronous by default.** Only Whisper transcription is a background job;
  every other LLM-heavy endpoint (translation, voice, images, compliance) is a
  plain request/response, accepted as a tradeoff for simplicity at current scale.
