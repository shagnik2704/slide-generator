# Slide Generator

AI-powered tool for generating Spoken Tutorial content: scripts, slides, and narrated videos from simple outlines.

**Live Demo**
- Backend API: `https://slide-generator-1.onrender.com`
- Frontend UI: `https://slide-generator-61ic.onrender.com`

---

## Features

| Feature | Description |
|:--------|:------------|
| **Script Generation** | LangGraph pipeline: outline → structured content → narration → visual cues |
| **Voice Generation** | Gemini TTS with WebSocket streaming, pause/resume, slide-by-slide preview |
| **Slides Generation** | Beamer LaTeX templates, auto-populated from scripts |
| **Compliance Checks** | Admin compliance (formatting) + Quality compliance (pedagogy) |
| **MediaWiki Export** | One-click export to Spoken Tutorial wiki table format |
| **Image Prompt Enhancement** | AI-enhanced prompts for slide visuals with review UI |
| **Outline Chat** | Interactive wizard to build course outlines step-by-step |

---

## Quick Start

### Prerequisites
- **Python 3.11** via [uv](https://github.com/astral-sh/uv): `curl -Ls https://astral.sh/uv/install.sh | sh`
- **Node.js 18+** (or use `uvx --from nodejs-bin@22`)
- **LaTeX** for PDF generation: `brew install --cask mactex-no-gui` (macOS) or `apt install texlive-full` (Linux)
- **FFmpeg** for video: `brew install ffmpeg` or `apt install ffmpeg`

### Backend
```bash
cd slide-generator
uv sync                          # Install Python deps
echo "GOOGLE_API_KEY=your_key" > .env
uv run python -m src.api         # Starts on http://localhost:8000
```

### Frontend
```bash
cd chatbot-ui
npm install && npm run dev       # Starts on http://localhost:5173
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ChatArea.jsx │──│ useChatArea  │──│ Modular Hooks        │  │
│  └──────────────┘  └──────────────┘  │ • useUploadHandlers  │  │
│                                       │ • useSidebarHandlers │  │
│                                       │ • useGenerationHndlr │  │
│                                       │ • useOutlineChat     │  │
│                                       │ • useExportHandlers  │  │
│                                       └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ upload.py  │  │generation.py│  │outline_chat│  │download  │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Pipeline                     │
│  detect_type → generate_structure → expand_narration →          │
│  generate_visuals → evaluator ⟳ optimiser → generate_pdf        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
slide-generator/
├── src/
│   ├── api/
│   │   ├── server.py              # FastAPI app, CORS, static mounts
│   │   ├── models.py              # Pydantic request/response models
│   │   └── routes/
│   │       ├── upload.py          # File uploads, parsing, compliance
│   │       ├── generation.py      # Script/slides/video generation
│   │       ├── download.py        # File downloads
│   │       └── outline_chat/      # Interactive outline wizard
│   ├── core/
│   │   ├── agent.py               # LangGraph workflow definition
│   │   └── state.py               # AgentState TypedDict
│   ├── nodes/                     # LangGraph processing nodes
│   └── services/                  # Business logic (PDF, LaTeX, TTS)
├── chatbot-ui/
│   └── src/
│       ├── components/            # React components
│       ├── hooks/                 # Modular React hooks (6 files)
│       └── services/api.js        # Centralized fetch wrapper
├── static/                        # Generated PDFs, videos
├── output/                        # Audio files, images
└── data/sample_scripts/           # Example scripts
```

---

## API Reference

### Upload & Parse
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/upload_outline` | POST | Parse outline file (TXT/DOCX) |
| `/upload_script` | POST | Parse script + run compliance |
| `/parse_script` | POST | Parse script only (no compliance) |

### Generation
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/generate_script` | POST | Outline → JSON script via LangGraph |
| `/generate_slides` | POST | JSON script → Beamer PDF |
| `/generate_video` | POST | Script + PDF → narrated video |
| `/ws/generate_voice` | WS | Streaming TTS with pause/resume |

### Compliance & Quality
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/check_compliance` | POST | Admin compliance checks |
| `/check_quality` | POST | Quality/pedagogy checks |

### Export
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/export_mediawiki` | POST | JSON → MediaWiki table format |
| `/download_script_docx` | POST | JSON → DOCX download |
| `/docx_to_mediawiki` | POST | DOCX → MediaWiki directly |

### Outline Chat
| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/outline_chat` | POST | Multi-turn outline builder |
| `/outline_chat/{id}/edit` | POST | Edit a previous answer |
| `/outline_chat/{id}/export` | GET | Export completed outline |

---

## Development

```bash
# Format Python (if configured)
uv run ruff format src/

# Run tests (if available)
uv run pytest

# Regenerate lock file
uv lock

# Production frontend build
cd chatbot-ui && npm run build
```

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python 3.11, FastAPI, LangGraph, Pydantic |
| Frontend | React 18, Vite, Lucide Icons |
| AI/LLM | Google Gemini (text + TTS) |
| PDF | LaTeX (Beamer), python-docx |
| Video | FFmpeg |
| Package Mgmt | uv (Python), npm (JS) |

---

## License

MIT
