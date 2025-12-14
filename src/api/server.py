"""FastAPI application server."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from src.api.routes import (
    upload_router,
    generation_router,
    download_router,
    outline_chat_router,
)

# Get project root
project_root = Path(__file__).parent.parent.parent

app = FastAPI(title="Slide Generator API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files to serve generated content
static_dir = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(outline_chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
