# Slide-Generator Agent Guidelines & Deployment Principles

This document defines the core development, testing, git workflow, and deployment principles for the `slide-generator` project. All AI agents operating in this workspace (Antigravity, Claude, Copilot, etc.) must follow these instructions.

---

## 1. Git Workflow & Branch Protection

- **Protected Main Branch**: `origin/main` has branch protection rules enforcing status checks. Direct pushes to `origin/main` are blocked by GitHub (`GH013`).
- **Feature Branch Workflow**:
  - Always create a dedicated branch for changes: `git checkout -b <type>/<description>` (e.g. `feat/...`, `fix/...`, `ci/...`, `chore/...`).
  - Keep commits clean, conventional, and self-contained.
- **Automated Merging (Zero Manual Merge Clicking)**:
  - The repository has **Auto-Merge enabled** (`allow_auto_merge: true`).
  - When code is ready to ship, push the branch and queue auto-merge using the GitHub CLI:
    ```bash
    git push -u origin <branch-name>
    gh pr create --fill # or --title "..." --body "..."
    gh pr merge --auto --squash --delete-branch
    ```
  - GitHub Actions runs the test suite. As soon as tests pass green, GitHub automatically squash-merges the PR into `main` and deletes the remote branch.
  - After merge, sync local `main`:
    ```bash
    git checkout main && git pull origin main
    ```

---

## 2. Pre-Push Quality Verification (CI Gates)

Before opening or auto-merging any PR, verify that all CI gates pass locally:

### Backend
- **Test Suite**: Run tests using Python 3.11 / `uv`:
  ```bash
  uv run python -m unittest discover tests
  ```
- **Secrets in CI**: CI runs with mock keys (`mock-openai-key-for-ci`, etc.). Ensure any top-level module imports do not crash when external API keys or DB connections are absent.

### Frontend (`chatbot-ui/`)
- **Linting**: Must pass with 0 errors and 0 warnings:
  ```bash
  cd chatbot-ui && npm run lint
  ```
  *(Note: ESLint ignores unused variables/parameters matching `^[A-Z_]`. Never declare inner React components inside renders).*
- **Build**: Must compile and bundle successfully:
  ```bash
  cd chatbot-ui && npm run build
  ```

---

## 3. Deployment Architecture & Principles

The production deployment runs via GitHub Actions (`.github/workflows/build.yml`) to a remote VM using Docker Compose.

### Core Deployment Principles:
1. **Pre-Deploy Database Backup**:
   - Before applying migrations or pulling new containers, create a timestamped `pg_dump` snapshot stored in `$PROJECT_PATH/backups/`:
     ```bash
     docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/db_backup_pre_deploy_$(date +%Y%m%d_%H%M%S).sql"
     ```
2. **Automated Rollback on Deploy Failure**:
   - Back up `.env` before updating `IMAGE_TAG`:
     ```bash
     cp .env .env.bak
     ```
   - If containers fail to launch or fail health checks within the timeout (24 attempts x 10s = 4 minutes), the pipeline must automatically restore `.env.bak`, rerun `docker compose up -d`, and exit with an error.
3. **Container Health Checking**:
   - Both `backend` and `whisper-worker` containers must reach `healthy` status before a deploy is marked successful.
   - If unhealthy, dump container logs (`docker compose logs --tail 50`) to surface the failure immediately.
4. **Grafana Provisioning Catch**:
   - Grafana datasources only update upon restart. Restart Grafana safely during deploy (`docker compose restart grafana || echo ...`) without failing the overall run.
