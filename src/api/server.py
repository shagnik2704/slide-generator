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
# CORS middleware
# Explicitly allow the deployed frontends and keep a permissive regex for staging.
allowed_origins = [
    "https://slide-generator-1.onrender.com",
    "https://slide-generator-61ic.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Mount static files to serve generated content
# Use check_dir=False so the app can start even if the directory
# doesn't exist yet on the deployment filesystem.
static_dir = project_root / "static"
app.mount("/static", StaticFiles(directory=str(static_dir), check_dir=False), name="static")

# Include routers
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(download_router)
app.include_router(outline_chat_router)

# Basic health/root endpoints for uptime checks
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
