# Project Structure

Detailed directory layout and architecture of the Slide Generator project.

## Directory Layout

```
slide-generator/
├── src/                              # Python backend
│   ├── api/                          # FastAPI layer
│   │   ├── __main__.py               # Entry point: python -m src.api
│   │   ├── server.py                 # FastAPI app, CORS, static mounts
│   │   ├── models.py                 # Pydantic request/response schemas
│   │   └── routes/
│   │       ├── upload.py             # File parsing, compliance checks
│   │       ├── generation.py         # Script/slides/video generation
│   │       ├── download.py           # File download endpoints
│   │       └── outline_chat/         # Interactive outline wizard (14 modules)
│   │           ├── outline_chat.py           # Main router
│   │           ├── outline_chat_models.py    # Pydantic models
│   │           ├── outline_chat_session.py   # Session management
│   │           ├── outline_chat_question_flow.py
│   │           ├── outline_chat_field_extraction.py
│   │           ├── outline_chat_validation.py
│   │           └── ...
│   │
│   ├── core/                         # Business logic
│   │   ├── agent.py                  # LangGraph workflow definition
│   │   └── state.py                  # AgentState TypedDict
│   │
│   ├── nodes/                        # LangGraph processing nodes
│   │   ├── type_detector.py          # Detect tutorial type (conceptual/demo)
│   │   ├── structure_node.py         # Generate structured outline
│   │   ├── narration_node.py         # Expand narration content
│   │   ├── visuals_node.py           # Generate visual cues
│   │   ├── evaluator_node.py         # Quality evaluation loop
│   │   ├── optimiser_node.py         # Script optimization
│   │   ├── pdf_node.py               # Script PDF generation
│   │   ├── slide_content_node.py     # Slide content extraction
│   │   ├── media_node.py             # Audio/image generation
│   │   ├── video_node.py             # Video assembly
│   │   └── _archive/                 # Deprecated nodes
│   │
│   ├── services/                     # Reusable business services
│   │   ├── voice_service.py          # Gemini TTS, batching, silence splitting
│   │   ├── compliance_service.py     # Admin compliance checks
│   │   ├── quality_service.py        # Quality/pedagogy checks
│   │   ├── docx_service.py           # DOCX parsing and export
│   │   ├── mediawiki_service.py      # MediaWiki table export
│   │   ├── beamer_service.py         # Beamer LaTeX generation
│   │   ├── latex_service.py          # LaTeX template rendering
│   │   ├── pdf_service.py            # PDF document creation
│   │   ├── image_service.py          # Image generation (Imagen)
│   │   ├── prompt_enhancer.py        # AI prompt enhancement
│   │   ├── content_extractor.py      # Content extraction utilities
│   │   ├── outline_service.py        # Outline generation
│   │   ├── outline_docx_service.py   # Outline DOCX export
│   │   └── outline_pdf_service.py    # Outline PDF export
│   │
│   ├── routing/                      # LangGraph routing logic
│   │   └── router.py                 # Conditional edge functions
│   │
│   └── utils/                        # Helper utilities
│       ├── audio_utils.py            # Audio file utilities
│       └── pdf_reader.py             # PDF text extraction
│
├── chatbot-ui/                       # React frontend
│   └── src/
│       ├── main.jsx                  # React entry point
│       ├── App.jsx                   # Root component
│       ├── index.css                 # Global styles
│       │
│       ├── components/               # React components (15 files)
│       │   ├── ChatArea.jsx          # Main chat interface
│       │   ├── InputArea.jsx         # Message input + file staging
│       │   ├── MessageBubble.jsx     # Individual message rendering
│       │   ├── Sidebar.jsx           # Feature sidebar
│       │   ├── ComplianceReport.jsx  # Compliance check display
│       │   ├── QualityReport.jsx     # Quality check display
│       │   ├── VoicePreview.jsx      # Audio preview player
│       │   ├── ImagePromptReview.jsx # Image prompt editor
│       │   ├── ImageGallery.jsx      # Generated images display
│       │   ├── WikiScriptEditor.jsx  # MediaWiki inline editor
│       │   ├── OutlineCard.jsx       # Outline display card
│       │   ├── SlidesPreview.jsx     # PDF slides preview
│       │   ├── Tooltip.jsx           # Custom tooltips
│       │   ├── ThemeToggle.jsx       # Dark/light mode
│       │   ├── Layout.jsx            # Page layout
│       │   └── message-actions/      # Action buttons (7 files)
│       │
│       ├── hooks/                    # Modular React hooks (6 files)
│       │   ├── useChatArea.js        # Orchestrator hook
│       │   ├── useUploadHandlers.js  # File upload handlers
│       │   ├── useSidebarHandlers.js # Sidebar feature handlers
│       │   ├── useGenerationHandlers.js # Script/slides generation
│       │   ├── useOutlineChat.js     # Outline chat logic
│       │   └── useExportHandlers.js  # Export/quality handlers
│       │
│       ├── services/
│       │   └── api.js                # Centralized fetch wrapper
│       │
│       └── utils/
│           └── chatStorage.js        # localStorage persistence
│
├── static/                           # Files served at /static/*
├── output/                           # Generated files
│   ├── pdfs/
│   ├── videos/
│   ├── images/
│   └── audio/                        # TTS audio files
├── uploads/                          # User uploads (temporary)
├── data/
│   └── sample_scripts/               # Few-shot learning examples
└── docs/                             # Documentation
```

## Architecture Decisions

### Backend
1. **LangGraph for orchestration** – Multi-step pipeline with conditional edges and evaluation loops
2. **FastAPI for HTTP** – Async support, automatic OpenAPI docs, Pydantic validation
3. **Services layer** – Business logic decoupled from HTTP routes
4. **Nodes as pure functions** – Each node takes state, returns partial state update

### Frontend
1. **Modular hooks** – Split 1,400-line hook into 6 focused modules
2. **Centralized API service** – All fetch calls go through `services/api.js`
3. **Component composition** – ChatArea orchestrates MessageBubble, InputArea, etc.
4. **localStorage persistence** – Session state survives page refresh

### Data Flow
```
User Upload → Parse → Compliance Check → LangGraph Pipeline → Generated Assets
                ↓
         JSON Script (source of truth)
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
  Slides      Audio       Video
```

## File Naming Conventions

| Pattern | Meaning |
|:--------|:--------|
| `*_node.py` | LangGraph processing node |
| `*_service.py` | Reusable business logic |
| `use*.js` | React custom hook |
| `*_chat_*.py` | Outline chat module |

## Running Locally

```bash
# Backend
uv run python -m src.api

# Frontend
cd chatbot-ui && npm run dev
```
