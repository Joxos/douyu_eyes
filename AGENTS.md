# AGENTS.md
Repository operating guide for coding agents in `douyu_eyes`.
Use this as the default operational contract unless overridden by newer local rule files.

## 1) Project Layout
- Backend: Python 3.12 + FastAPI + SQLModel + Pydantic.
  - Key files: `backend/main.py`, `backend/db.py`, `backend/schemas.py`
  - Tooling config: `pyproject.toml`, `requirements.txt`
- Frontend: Vue 3 + Vite (JavaScript) + Vue Router.
  - Key files: `frontend/src/**`, `frontend/vite.config.js`
- E2E tests: Playwright.
  - Key files: `frontend/playwright.config.js`, `frontend/tests-e2e/*.spec.js`

## 2) Setup and Run
### Backend (repo root)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Alternative (`scripts/dev.sh` uses this when available):
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```
Run backend API:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend (`frontend/`)
```bash
cd frontend
pnpm install
pnpm dev
```
Build frontend:
```bash
cd frontend
pnpm build
```

## 3) Build / Lint / Test Commands
### Backend (repo root)
Run all tests:
```bash
pytest
```
Run a single file:
```bash
pytest tests/test_api_endpoints.py
```
Run a single test function:
```bash
pytest tests/test_api_endpoints.py::test_search_endpoint_basic_success
```
Run by keyword:
```bash
pytest -k "search and invalid_sort"
```
Lint and format:
```bash
ruff .
black .
```

### Frontend Playwright (`frontend/`)
Run full suite:
```bash
pnpm run test:e2e
```
Run one spec file:
```bash
pnpm run test:e2e -- tests-e2e/search-sort.spec.js
```
Run one test by title:
```bash
pnpm run test:e2e -- -g "search pagination metadata and button state are usable"
```
Run file at line:
```bash
pnpm run test:e2e -- tests-e2e/search-pagination.spec.js:3
```
Direct CLI equivalents:
```bash
pnpm exec playwright test
pnpm exec playwright test tests-e2e/search-sort.spec.js
pnpm exec playwright test -g "search sort=count"
```

## 4) Environment and Runtime Assumptions
- DB-backed behavior requires `DYKIT_DSN`.
  - Without it, DB-heavy tests intentionally skip (`tests/test_api_endpoints.py`).
  - DSN is typically exported in shell startup files (for this machine it is in `~/.zshrc`), but **never copy credentials into repo docs/code/tests**.
  - Safe DB schema inspection examples:
    - `source ~/.zshrc && psql "$DYKIT_DSN" -c "SELECT current_database(), current_user"`
    - `source ~/.zshrc && psql "$DYKIT_DSN" -c "\dt public.*"`
    - `source ~/.zshrc && psql "$DYKIT_DSN" -c "\d+ public.danmaku"`
- Backend default filters/limits live in `backend/db.py` constants:
  - `ROOM_ID`, `MSG_TYPE`, `MAX_KEYWORDS`, `MAX_LIMIT`, `DEFAULT_LIMIT`
- Unique-content aggregate sync lives in backend code:
  - Tables: `public.danmaku_unique_stats`, `public.danmaku_sync_state`
  - Sync function: `backend.db.run_incremental_unique_sync`
  - Uvicorn in-process periodic sync: `UNIQUE_SYNC_INTERVAL_SECONDS` (default 30s, min 5s)
- Search endpoint contract (`/api/search`):
  - Query params: `q`, `limit`, `offset`, `sort`
  - `sort` allowed values: `count`, `last_seen`
  - Response includes: `items`, `limit`, `offset`, `total`, `total_pages`, `current_page`
- Helper script `scripts/dev.sh` starts backend + frontend together.

## 5) Coding Conventions
### Python backend
- Follow `ruff` + `black` defaults (`line-length = 88` in `pyproject.toml`).
- Keep imports explicit and grouped at the file top.
- Prefer typed signatures and explicit return types.
- Keep data/business logic in `backend/db.py`; keep HTTP mapping in `backend/main.py`.
- Raise specific exceptions in lower layers (`ValueError`, `LookupError`, `RuntimeError`).
- Convert exceptions to `HTTPException` at route boundaries with accurate status codes.
- Reuse existing helpers/constants (`parse_keywords`, `normalize_limit`, `MAX_*`).
- Do not silently truncate/ignore invalid user input beyond existing helper behavior.

### Frontend (Vue)
- Use `<script setup>` with Composition API (`ref`, `computed`, lifecycle hooks).
- Keep request state explicit: `loading`, `error`, `results`, pagination refs.
- Keep async fetch flow explicit with `try/catch/finally`.
- Naming: camelCase in JS, kebab-case for CSS classes.
- Preserve `data-testid` attributes used by Playwright tests.

### API contract policy (strict)
- Backend and frontend are both controlled in this repo: treat schema as strict.
- Do not add defensive schema-drift fallbacks like:
  - `data.results || data.data || []`
  - guessing alternate response keys
- If shape is wrong, fail fast and fix producer/consumer directly.

## 6) Error Handling Rules
- Never swallow exceptions silently in new code.
- Backend:
  - either translate to `HTTPException` with clear status/detail,
  - or re-raise intentionally.
- Frontend:
  - surface human-readable messages through UI state (`error.value`).
- Keep validation and contract failures explicit.

## 7) Testing Discipline for Changes
- Sync rule (non-negotiable): docs (including `AGENTS.md`), code, and tests must be updated together in the same change set when behavior/contracts change.
- Backend changes:
  1. `ruff .`
  2. `black .` (or targeted files)
  3. targeted `pytest` first, then broader relevant tests
- Frontend/API interaction changes:
  1. run impacted Playwright specs
  2. run full `pnpm run test:e2e` before finalizing substantial work
- E2E prerequisites/notes:
  - Playwright config starts frontend web server on `127.0.0.1:4173` automatically.
  - Backend must be running separately on `127.0.0.1:8000` with valid `DYKIT_DSN`.
  - Useful regressions to keep green:
    - `tests-e2e/search-pagination.spec.js`
    - `tests-e2e/search-pagination-rapid-click.spec.js`
    - `tests-e2e/search-sort.spec.js`
- Prefer smallest targeted test while iterating, then broaden coverage.

## 9) Repo Hygiene (important)
- Do not commit runtime/generated artifacts:
  - `frontend/test-results/`, `frontend/playwright-report/`, `frontend/dist/`, caches.
- Do not commit secrets or DSN values; use env vars only.

## 8) Rule File Discovery (Cursor / Copilot)
- `.cursor/rules/`: not found in this repository.
- `.cursorrules`: not found in this repository.
- `.github/copilot-instructions.md`: not found in this repository.

If any of these files are added later, treat them as higher-priority instructions and update this AGENTS.md accordingly.
