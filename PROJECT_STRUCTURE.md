# Project Structure

This document describes the professional folder structure of the Slide Generator project.

## Directory Layout

```
slide-generator/
├── src/                          # Main application source code
│   ├── api/                      # FastAPI server and API routes
│   │   ├── __init__.py
│   │   ├── __main__.py           # Entry point for running server
│   │   ├── server.py             # FastAPI application
│   │   └── routes/               # API route handlers (future expansion)
│   │       └── __init__.py
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── agent.py              # Main agent workflow (LangGraph)
│   │   └── state.py              # Agent state management
│   ├── nodes/                     # Processing nodes for the agent graph
│   │   ├── __init__.py
│   │   ├── evaluator_node.py     # Quality evaluation
│   │   ├── media_node.py         # Image/video generation
│   │   ├── narration_node.py     # Narration expansion
│   │   ├── optimiser_node.py     # Script optimization
│   │   ├── outline_node.py       # Outline processing
│   │   ├── pdf_node.py           # PDF generation
│   │   ├── script_node.py        # Script generation
│   │   ├── slide_content_node.py # Slide content generation
│   │   ├── structure_node.py     # Structure generation
│   │   ├── type_detector.py      # Tutorial type detection
│   │   ├── video_node.py         # Video creation
│   │   └── visuals_node.py      # Visual generation
│   ├── routing/                   # Routing logic for agent workflow
│   │   ├── __init__.py
│   │   └── router.py             # Route step and evaluation logic
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── latex_service.py      # LaTeX template rendering
│   │   ├── outline_service.py     # Outline document generation
│   │   └── pdf_service.py        # PDF document creation
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── audio_utils.py         # Audio processing utilities
│       └── pdf_reader.py          # PDF reading utilities
│
├── chatbot-ui/                    # Frontend React application
│   ├── src/
│   │   ├── components/           # React components
│   │   └── ...
│   └── ...
│
├── static/                        # Static files served by API
│   └── logo.png                  # Application logo
│
├── output/                        # Generated output files
│   ├── pdfs/                      # Generated PDF files
│   ├── videos/                   # Generated video files
│   └── images/                    # Generated image files
│
├── uploads/                       # User-uploaded files (temporary)
│
├── data/                          # Sample data and templates
│   └── sample_scripts/           # Sample scripts for few-shot learning
│       ├── json/                  # JSON sample scripts
│       └── *.pdf                  # PDF sample scripts
│
├── docs/                          # Documentation
│   └── script_pipeline.md        # Pipeline documentation
│
├── tests/                         # Test files (to be implemented)
│
├── .gitignore                     # Git ignore rules
├── pyproject.toml                 # Python project configuration
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
└── render.yaml                    # Deployment configuration
```

## Key Design Decisions

1. **Separation of Concerns**: 
   - `api/` - HTTP layer and routing
   - `core/` - Business logic and state
   - `nodes/` - Individual processing steps
   - `services/` - Reusable business services
   - `utils/` - Helper functions

2. **Clear Output Organization**:
   - `static/` - Files served via HTTP
   - `output/` - Generated files organized by type
   - `uploads/` - Temporary user uploads

3. **Data Organization**:
   - `data/` - Sample data and templates
   - `docs/` - Documentation

4. **Import Structure**:
   - All imports use `src.` prefix for clarity
   - Absolute imports from project root

## Running the Application

```bash
# Run the server
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

# Or use the entry point
uv run python -m src.api
```
