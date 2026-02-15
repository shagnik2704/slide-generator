# Spoken Tutorial Generator

AI-powered platform for generating Spoken Tutorial content — scripts, slides, voice narration, images, and translations — from simple outlines. Built for the [Spoken Tutorial Project](https://spoken-tutorial.org/) at IIT Bombay.

**Live:** [spokenai.live](https://spokenai.live)

---

## Features

| Feature | Description |
|:--------|:------------|
| **Script Generation** | LangGraph multi-node pipeline: outline → structured content → narration → visual cues with evaluator/optimiser loop |
| **Voice Generation** | Google Gemini TTS — per-slide audio with ZIP download, or single combined audio for a full tutorial |
| **Slides Generation** | Beamer LaTeX templates, auto-populated from scripts via LLM content extraction |
| **Image Generation** | AI-enhanced prompts → image generation with prompt review UI, reference image upload, and per-image editing |
| **Compliance Checks** | Admin compliance (formatting, structure) + quality compliance (pedagogy, back-translation) |
| **Translation** | Multi-language batch translation with translation grid, per-cell editing, and per-cell TTS |
| **Slides Translation** | Translate `.tex` Beamer files to 11+ Indian languages with XeLaTeX Unicode support |
| **Timed Script** | Upload audio → Whisper transcription → sentence-level timestamps with DOCX export |
| **MediaWiki Export** | One-click export to Spoken Tutorial wiki table format (from JSON or DOCX) |
| **Outline Chat** | Phased SME interview (warmup → outcomes → examples → structure → metadata → review) with session persistence, streaming SSE, field editing, validation, and PDF/JSON export (14 submodules) |
| **Version Change Automation** | Scrapes spoken-tutorial.org → LLM + Tavily web search for version updates → splits long tutorials into 3-4 min fragments → tabulates old-vs-new comparison → exports to Google Sheets via Workload Identity Federation |
| **Batch Processing** | Batch compliance checks and quality checks for multiple scripts in parallel |
| **Google OAuth** | Domain-restricted Google authentication with JWT tokens |

---

## Quick Start

### Prerequisites
- **Python 3.11** via [uv](https://github.com/astral-sh/uv): `curl -Ls https://astral.sh/uv/install.sh | sh`
- **Node.js 18+**
- **LaTeX** for PDF generation: `brew install --cask mactex-no-gui` (macOS) or `apt install texlive-full` (Linux)
- **FFmpeg** for audio/video: `brew install ffmpeg` or `apt install ffmpeg`

### Backend
```bash
cd slide-generator
cp .env.example .env           # Add your API keys
uv sync                        # Install Python deps
uv run python -m src.api       # Starts on http://localhost:8000
```

### Frontend
```bash
cd chatbot-ui
npm install && npm run dev     # Starts on http://localhost:5173
```

### Docker (Production)
```bash
docker compose up --build -d   # Backend + Frontend (Nginx) + Monitoring
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React 19 + Vite)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────────┐ │
│  │ ChatArea.jsx │──│ useChatArea  │──│ Modular Hooks                  │ │
│  │              │  │              │  │ • useUploadHandlers            │ │
│  │ 33 components│  └──────────────┘  │ • useSidebarHandlers           │ │
│  │ + 7 hooks    │                    │ • useGenerationHandlers        │ │
│  └──────────────┘                    │ • useOutlineChat               │ │
│                                      │ • useExportHandlers            │ │
│                                      │ • useRedesignHandlers          │ │
│                                      └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                              │ HTTP / WebSocket
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI + Python 3.11)                    │
│                                                                          │
│  Routes (14 modules)           Services (20 modules)                     │
│  ├── auth.py                   ├── voice_service.py                      │
│  ├── upload.py                 ├── image_service.py                      │
│  ├── generation.py             ├── compliance_service.py                 │
│  ├── compliance.py             ├── quality_service.py                    │
│  ├── quality.py                ├── translation_service.py                │
│  ├── voice.py                  ├── slides_translation_service.py         │
│  ├── images.py                 ├── timed_script_service.py               │
│  ├── slides.py                 ├── beamer_service.py                     │
│  ├── translation.py            ├── content_extractor.py                  │
│  ├── slides_translation.py     ├── mediawiki_service.py                  │
│  ├── timed_script.py           ├── docx_service.py                       │
│  ├── download.py               ├── pdf_service.py                        │
│  ├── outline_chat/             ├── prompt_enhancer.py                    │
│  └── redesign.py               └── database.py (SQLite + SQLAlchemy)     │
│                                                                          │
│  Core                          Nodes (LangGraph pipeline)                │
│  ├── agent.py (workflow)       ├── metadata_node.py                      │
│  └── state.py (AgentState)     ├── content_node.py                       │
│                                ├── boilerplate_node.py                   │
│                                ├── merge_node.py                         │
│                                └── split.py, extraction.py, ...          │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Infrastructure & AI                              │
│                                                                          │
│  AI/LLM: Google Gemini (text + TTS + image gen) + OpenAI (via LangChain)│
│  Search: Tavily API (for knowledge graph / RAG)                          │
│  STT: OpenAI Whisper (local, base model)                                 │
│  DB: SQLite (translations) via SQLAlchemy                                │
│  Auth: Google OAuth 2.0 → JWT                                            │
│  Deploy: Docker Compose + Nginx (SSL) on GCP VM                          │
│  CI/CD: GitHub Actions → SSH deploy                                      │
│  Monitoring: Prometheus + Grafana + cAdvisor                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Workflows

### Script Generation Pipeline (`src/core/agent.py`)

A LangGraph state machine that transforms an outline into a complete Spoken Tutorial script:

```
Outline → metadata_node → boilerplate_node → content_node → merge_node → Evaluator
                                                                            ↓
                                                                    Pass? → Final JSON Script
                                                                    Fail? → Loop back with feedback
```

- **metadata_node** — Extracts title, module, episode, learning objectives, duration, prerequisites from outline
- **boilerplate_node** — Generates 7 standard Spoken Tutorial slides (title, objectives, prerequisites, etc.)
- **content_node** — Generates content + demo slides with narration and visual cues
- **merge_node** — Merges boilerplate + content into final slide deck
- **Evaluator loop** — Validates pedagogy compliance and reruns problematic slides (max iterations)
- State: `AgentState` TypedDict with 20+ fields tracking the full pipeline

### Outline Chat (`src/api/routes/outline_chat/`, 14 submodules)

A structured, multi-turn chatbot that guides Subject Matter Experts through course outline creation following Spoken Tutorial pedagogy rules:

```
Phase A (Warmup)  →  Phase B (Outcomes)  →  Phase C (Examples)
       ↓                                           ↓
Phase D (Structure)  →  Phase E (Metadata)  →  Review  →  Approved
```

| Module | Purpose |
|:-------|:--------|
| `outline_chat.py` | Main router — chat, streaming SSE, export, field edit, snapshot, general chat |
| `outline_chat_models.py` | Pydantic models (`CourseOutlineData`, `TutorialRow`, `ConversationPhase`) |
| `outline_chat_question_flow.py` | Phase-aware question sequencing per outline type (FOSS/ICT/Other) |
| `outline_chat_extraction.py` | LLM-based extraction of structured data from free-text answers |
| `outline_chat_field_extraction.py` | Targeted extraction for specific fields |
| `outline_chat_processing.py` | Answer processing and outline data assembly |
| `outline_chat_validation.py` | Pedagogy compliance validation of the assembled outline |
| `outline_chat_draft_generation.py` | Generates draft outline from collected data |
| `outline_chat_llm_utils.py` | LLM prompt construction and invocation helpers |
| `outline_chat_handlers.py` | Phase transition and branching logic |
| `outline_chat_responses.py` | Response formatting and confirmation building |
| `outline_chat_session.py` | Session persistence (load/save) |
| `outline_chat_edit.py` | Post-hoc field editing with re-validation |

Features: streaming token-by-token SSE, general chat with web search (Tavily), outline snapshot endpoint, PDF and JSON export, CORS preflight handling.

### Version Change Automation (`src/workflow.py` + `src/nodes/`)

A pipeline that modernizes legacy Spoken Tutorial course outlines by finding version updates and restructuring tutorials:

```
FOSS Name + Language
       ↓
  extract_links.py     → Scrape tutorial list from spoken-tutorial.org
       ↓
  extraction.py        → Fetch each tutorial page, extract title/duration/subtopics (BeautifulSoup)
       ↓  (semaphore: 8 concurrent)
  updates.py           → LLM + Tavily search per tutorial → find version changes, deprecations
       ↓  (semaphore: 2 concurrent — rate limited)
  split.py             → LLM splits long tutorials (>4 min) into 3-4 min fragments
       ↓  (semaphore: 4 concurrent)
  tabulate.py          → Build old-vs-new comparison table (Old T# / New T# / Logs)
       ↓
  gsheet.py            → Copy template → upload data → share with recipients
```

- State: `VCAgentState` TypedDict (`legacy_raw_data`, `structured_legacy`, `tech_updates`, `final_table`)
- Auth: Google Workload Identity Federation (keyless, via Application Default Credentials)
- Export: Creates a Google Sheet from a template, uploads the comparison table, shares with specified emails

---

## Project Structure

```
slide-generator/
├── src/
│   ├── api/
│   │   ├── server.py                # FastAPI app, CORS, middleware, static mounts
│   │   ├── config.py                # Pydantic Settings (env validation)
│   │   ├── auth.py                  # JWT creation/verification, email domain validation
│   │   ├── middleware.py            # Security headers + request logging
│   │   ├── exceptions.py           # Custom HTTP exception classes
│   │   ├── models.py               # Pydantic request/response models
│   │   └── routes/
│   │       ├── auth.py             # Google OAuth login/callback/verify/logout
│   │       ├── upload.py           # File uploads (outline, script parsing)
│   │       ├── generation.py       # Script gen, video gen, MediaWiki export, DOCX
│   │       ├── compliance.py       # Compliance checks (single, batch, outline, export)
│   │       ├── quality.py          # Quality checks with back-translation
│   │       ├── voice.py            # TTS (per-slide + combined audio)
│   │       ├── images.py           # Prompt enhancement, image gen, image editing
│   │       ├── slides.py           # Beamer LaTeX slide generation
│   │       ├── translation.py      # Multi-language translation + translation grid
│   │       ├── slides_translation.py  # .tex file translation (11+ languages)
│   │       ├── timed_script.py     # Audio → timestamped transcript (Whisper)
│   │       ├── download.py         # File downloads (outline, images, ZIPs)
│   │       ├── outline_chat/       # Phased SME interview chatbot (14 submodules)
│   │       └── redesign.py         # Version Change Automation + Google Sheets
│   ├── core/
│   │   ├── agent.py                # LangGraph workflow graph definition
│   │   └── state.py                # AgentState TypedDict
│   ├── nodes/                      # Pipeline processing nodes
│   │   ├── metadata_node.py        # Script gen: extract tutorial metadata
│   │   ├── content_node.py         # Script gen: generate slide content
│   │   ├── boilerplate_node.py     # Script gen: generate boilerplate slides
│   │   ├── merge_node.py           # Script gen: merge generated content
│   │   ├── extraction.py           # VC pipeline: scrape tutorial pages (BeautifulSoup)
│   │   ├── extract_links.py        # VC pipeline: fetch tutorial links from spoken-tutorial.org
│   │   ├── updates.py              # VC pipeline: LLM + Tavily search for version changes
│   │   ├── split.py                # VC pipeline: split long tutorials into 3-4 min fragments
│   │   ├── tabulate.py             # VC pipeline: build old-vs-new comparison table
│   │   └── gsheet.py               # VC pipeline: Google Sheets export (WIF auth)
│   ├── services/                   # Business logic layer
│   │   ├── voice_service.py        # Gemini TTS generation
│   │   ├── image_service.py        # Image generation (Gemini Imagen)
│   │   ├── prompt_enhancer.py      # Visual cue → detailed prompt enhancement
│   │   ├── compliance_service.py   # Admin + pedagogy compliance checks
│   │   ├── quality_service.py      # Back-translation quality verification
│   │   ├── translation_service.py  # Multi-language script translation
│   │   ├── slides_translation_service.py  # .tex file translation
│   │   ├── timed_script_service.py # Whisper transcription + timing
│   │   ├── beamer_service.py       # LaTeX Beamer template generation
│   │   ├── content_extractor.py    # LLM-based slide content extraction
│   │   ├── mediawiki_service.py    # MediaWiki table formatting
│   │   ├── docx_service.py         # DOCX import/export
│   │   ├── pdf_service.py          # PDF generation
│   │   ├── outline_service.py      # Outline parsing (DOCX/MD/TXT/ODT)
│   │   ├── outline_docx_service.py # Outline DOCX export
│   │   ├── outline_pdf_service.py  # Outline PDF export
│   │   ├── latex_service.py        # LaTeX compilation
│   │   ├── image_styles.py         # Image style definitions
│   │   └── database.py             # SQLAlchemy models + CRUD (SQLite)
│   ├── utils/
│   │   ├── VC_utils.py             # LLM initialization, search tools
│   │   └── audio_utils.py          # WAV file utilities
│   └── models/                     # (reserved)
├── chatbot-ui/                     # Frontend React application
│   └── src/
│       ├── components/             # 33 React components
│       │   ├── ChatArea.jsx        # Main chat interface
│       │   ├── ImageWorkflow.jsx   # Image generation workflow
│       │   ├── ComplianceReport.jsx  # Compliance results display
│       │   ├── QualityReport.jsx   # Quality check results
│       │   ├── TranslationResults.jsx  # Translation grid
│       │   ├── VoicePreview.jsx    # Audio playback
│       │   ├── OutlineCard.jsx     # Outline builder
│       │   ├── WorkflowCard.jsx    # Workflow progress display
│       │   ├── Login.jsx           # Google OAuth login page
│       │   └── ...                 # + 24 more
│       ├── hooks/                  # 7 modular React hooks
│       └── services/api.js        # Centralized fetch wrapper
├── data/                          # SQLite database
├── static/                        # Static assets (logos, generated PDFs)
├── output/                        # Generated files (audio, images, slides)
├── uploads/                       # Temporary upload storage
├── docs/                          # Design documents & Architecture notes
├── docker-compose.yml             # Multi-container deployment
├── Dockerfile                     # Backend container (Python + FFmpeg + Whisper)
├── prometheus.yml                 # Monitoring configuration
└── .github/workflows/deploy.yml   # CI/CD: push to main → deploy to VM
```

---

## API Reference

### Authentication
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/auth/google` | GET | Initiate Google OAuth flow |
| `/auth/google/callback` | GET | OAuth callback, issues JWT |
| `/auth/verify` | POST | Verify JWT token |
| `/auth/logout` | POST | Logout (client-side) |

### Upload & Parse
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/upload_outline` | POST | Parse outline file (.md, .docx, .txt, .odt) |
| `/upload_script` | POST | Parse script + run compliance checks |
| `/parse_script` | POST | Parse script only (no checks) |

### Generation
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/generate_script` | POST | Outline → JSON script via LangGraph pipeline |
| `/generate_slides` | POST | JSON script → Beamer LaTeX + ZIP |
| `/generate_video` | POST | Script + PDF → narrated video |
| `/upload_edited_script` | POST | Upload edited .docx, convert back to JSON |

### Compliance & Quality
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/check_compliance` | POST | Run compliance checks on a script |
| `/check_outline_compliance` | POST | Run compliance checks on an outline |
| `/upload_outline_compliance` | POST | Upload outline file + run compliance |
| `/batch_check_compliance` | POST | Batch compliance for multiple scripts |
| `/export_compliance_report` | POST | Export report as DOCX/ODT |
| `/check_quality` | POST | Quality check with back-translation |
| `/batch_check_quality` | POST | Batch quality for multiple scripts |

### Voice
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/generate_voice` | POST | Per-slide TTS audio + ZIP |
| `/generate_voice_combined` | POST | Single combined audio for full tutorial |

### Images
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/enhance_prompts` | POST | Visual cues → detailed image prompts |
| `/generate_images` | POST | Prompts → generated images + ZIP |
| `/upload_reference_image` | POST | Upload reference for image-to-image |
| `/modify_image` | POST | Edit existing generated image |

### Translation
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/translation/languages` | GET | List supported languages |
| `/translation/translate` | POST | Translate to single language |
| `/translation/batch` | POST | Translate to multiple languages |
| `/translation/update-cell` | POST | Edit a translation grid cell |
| `/translation/project/{id}` | GET | Get project translation grid |
| `/translation/generate-audio` | POST | TTS for a specific cell |
| `/translation/export-docx` | POST | Export translation as DOCX |

### Slides Translation
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/slides-translation/languages` | GET | Supported slide translation languages |
| `/translate_slides` | POST | Translate .tex file to target language |

### Timed Script
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/timed-script/generate` | POST | Audio → timestamped transcript (Whisper) |
| `/timed-script/download-docx` | POST | Export timed script as DOCX |

### Export & Download
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/export_mediawiki` | POST | JSON → MediaWiki table format |
| `/docx_to_mediawiki` | POST | DOCX → MediaWiki directly |
| `/download_script_docx` | POST | JSON → editable Word document |
| `/download/outline/{filename}` | GET | Download outline file |
| `/download/image/{project}/{file}` | GET | Download generated image |
| `/download/zip/{project}/{file}` | GET | Download image ZIP |

### Outline Chat
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/outline_chat` | POST | Multi-turn phased outline builder |
| `/outline_chat/stream` | POST | Streaming SSE version (token-by-token) |
| `/outline_chat/{id}/snapshot` | GET | Human-readable outline snapshot |
| `/outline_chat/{id}/edit` | POST | Edit a specific field in outline data |
| `/outline_chat/{id}/export` | GET | Export outline as JSON or PDF |
| `/outline_chat/general` | POST | General chat with web search (Tavily) |

### Version Change Automation
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/redesign/generate` | POST | Scrape → update → split → tabulate → export pipeline |
| `/redesign/share` | POST | Share generated Google Sheet with recipients |

---

## Deployment

### Production (GCP VM)

The app is deployed via GitHub Actions CI/CD:
1. Push to `main` triggers the deploy workflow
2. GitHub Actions authenticates to GCP via Workload Identity Federation
3. SSHs into the VM and runs `docker compose up --build -d`

The Docker setup runs:
- **Backend container** — Python 3.11 + FFmpeg + Whisper (port 8000)
- **Frontend container** — Nginx serving built React app (ports 80/443) + reverse proxy to backend
- **Prometheus** — Metrics collection (port 9090)
- **Grafana** — Metrics dashboards (port 3000)
- **cAdvisor** — Container resource monitoring (port 8080)

### SSL / HTTPS
SSL certificates are managed via Let's Encrypt (certbot) on the host VM and mounted into the Nginx container.

---

## Development

```bash
# Format Python
uv run ruff format src/

# Regenerate lock file
uv lock

# Production frontend build
cd chatbot-ui && npm run build
```

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python 3.11, FastAPI, LangGraph, LangChain, Pydantic, SQLAlchemy |
| Frontend | React 19, Vite, Lucide Icons, React Router |
| AI/LLM | Google Gemini (text, TTS, image gen), OpenAI (via LangChain) |
| Search | Tavily API (web search for outline chat + version change pipeline) |
| Web Scraping | aiohttp, BeautifulSoup4 |
| STT | OpenAI Whisper (local) |
| PDF/Slides | LaTeX (Beamer), python-docx, ReportLab, PyMuPDF |
| Auth | Google OAuth 2.0, python-jose (JWT) |
| Database | SQLite + SQLAlchemy |
| Video | FFmpeg, MoviePy |
| Infra | Docker Compose, Nginx, GitHub Actions CI/CD |
| Monitoring | Prometheus, Grafana, cAdvisor |
| Package Mgmt | uv (Python), npm (JS) |

---

## License

MIT
