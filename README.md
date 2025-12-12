## Slide Generator

FastAPI backend plus a Vite/React chatbot UI for generating lesson outlines, narration, slides, and media. This README documents setup using **uv** for Python dependency management and **uvx** for Node/NPM binaries.

## Prerequisites
- uv installed: `curl -Ls https://astral.sh/uv/install.sh | sh`
- Python 3.10–3.12 (repo targets 3.11). Install with uv if needed: `uv python install 3.11`
- System packages: LaTeX (texlive-base/extra) and `ffmpeg` for PDF/video generation  
  - macOS (Homebrew): `brew install --cask mactex-no-gui` and `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-fonts-extra texlive-latex-extra ffmpeg`
- (Optional) For Node without a global install, uvx can fetch a portable binary via `nodejs-bin`.

## Backend (FastAPI)
1) From repo root, create a virtual env and install deps:
```
uv sync
```
2) Configure secrets in `.env`:
```
GOOGLE_API_KEY=your_key_here
```
3) Run the API (reload enabled):
```
uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
Static assets are served from `static/` at `/static/*`.

## Frontend (Vite/React chatbot UI)
The UI lives in `chatbot-ui/`. You can run Node via uvx + nodejs-bin (no global Node required):
```
cd chatbot-ui
uvx --from nodejs-bin@22 npm install
uvx --from nodejs-bin@22 npm run dev -- --host --port 5173
```
Production build:
```
uvx --from nodejs-bin@22 npm run build
```
The build output lands in `chatbot-ui/dist/` (served statically in deployment).

## Running full stack locally
- Start backend: `uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload`
- Start frontend: `cd chatbot-ui && uvx --from nodejs-bin@22 npm run dev -- --host --port 5173`
- The frontend expects the API at `http://localhost:8000`; CORS is open by default.

## Useful commands
- Format/ruff-equivalent not configured; rely on uv sync for dependency locks.
- Regenerate lock after dependency changes: `uv lock`
- Clean installs: remove `.venv` and rerun `uv sync`

## Notesre
- Generated PDFs/videos are written under `static/` and `generated_images/`.
- Sample outlines/scripts live under `sample_scripts/`.
