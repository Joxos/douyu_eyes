# AGENTS.md

Agent operating guide for `douyu_eyes`.
This file is for coding agents working in this repository.

## 1) Repo map

- Backend: Python 3.12, FastAPI, SQLModel
  - `backend/main.py` (HTTP routes, startup/shutdown, exception mapping)
  - `backend/db.py` (DB logic, constants, sync jobs)
  - `backend/schemas.py` (Pydantic response models)
- Backend tests: `tests/*.py`
- Frontend: Vue 3 + Vite (JavaScript)
  - `frontend/src/views/*.vue`
  - `frontend/src/router/index.js`
- E2E tests: Playwright in `frontend/tests-e2e/*.spec.js`

## 2) Setup and run

### Backend (repo root)

```bash
uv sync --dev
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend (`frontend/`)

```bash
pnpm install
pnpm dev
```

### Full-stack helper

- `scripts/dev.sh` starts backend + frontend together.

## 3) Build / lint / test commands

### Backend (repo root)

```bash
# run tests
uv run pytest

# run one test file
uv run pytest tests/test_api_endpoints.py

# run one test case
uv run pytest tests/test_api_endpoints.py::test_search_endpoint_basic_success

# run by keyword expression
uv run pytest -k "search and invalid_sort"

# lint / format / typecheck
uv run ruff check .
uv run black .
uv run basedpyright .
```

### Frontend (`frontend/`)

```bash
# dev / build
pnpm dev
pnpm build

# run all e2e
pnpm run test:e2e

# run one spec file
pnpm run test:e2e -- tests-e2e/search-sort.spec.js

# run one test by title
pnpm run test:e2e -- -g "search sort=count"

# run one test by file:line
pnpm run test:e2e -- tests-e2e/search-pagination.spec.js:3
```

### Direct Playwright CLI equivalents (`frontend/`)

```bash
pnpm exec playwright test
pnpm exec playwright test tests-e2e/search-sort.spec.js
pnpm exec playwright test -g "search sort=count"
```

## 4) Runtime assumptions and env

- DB-backed backend behavior requires `DYKIT_DSN`.
- If `DYKIT_DSN` is missing, DB-heavy tests intentionally skip.
- Do not commit DSN values, credentials, or local shell exports.
- Playwright web server config is in `frontend/playwright.config.js`:
  - starts `pnpm dev --host 127.0.0.1 --port 4173 --strictPort`
  - uses `baseURL: http://127.0.0.1:4173`
- For full E2E validity, backend should be running on `127.0.0.1:8000`.

## 5) Code style conventions (observed in repo)

### Language policy (UI vs development)

- User-facing website/app text should be displayed in Chinese.
- Development-facing artifacts should remain in English:
  - code identifiers (variables, functions, classes)
  - file/directory names
  - test descriptions/titles
  - commit messages and most inline technical comments

### Python backend

- Formatting/tooling is defined in `pyproject.toml`:
  - Ruff + Black with line length 88.
- Imports are explicit and grouped at top of file.
- Modern typing syntax is used (`int | None`, `list[str]`).
- Naming:
  - constants: `UPPER_SNAKE_CASE` (`ROOM_ID`, `MAX_LIMIT`)
  - functions/vars: `snake_case`
  - classes: `PascalCase`
- Layering:
  - DB/business logic in `backend/db.py`
  - HTTP request validation + response mapping in `backend/main.py`
- API contracts are explicit with Pydantic models in `backend/schemas.py`.
- Prefer specific exceptions in lower layers (`ValueError`, `LookupError`, `RuntimeError`).
- Convert errors to `HTTPException` at route boundaries with proper status codes.

### Frontend (Vue)

- Use Vue SFCs with `<script setup>` and Composition API.
- Use `ref`, `computed`, `onMounted`, `onUnmounted` patterns already present.
- JS variable names are `camelCase`; CSS classes are `kebab-case`.
- Keep request state explicit: loading, error, results, pagination values.
- Use `try/catch/finally` for async fetch flows.
- Preserve `data-testid` attributes used by Playwright tests.
- Keep backend contract usage strict:
  - consume known keys like `items`, `total`, `total_pages`, `current_page`
  - avoid speculative fallback schemas (`data.results || data.data || []`).

## 6) Error-handling rules

- Project phase rule (strict): do not apply defensive-programming fallbacks that hide invalid states.
  - For unexpected/invalid behavior, fail fast and raise/throw explicit errors.
  - Do not silently coerce unknown values to placeholders to "make UI continue".
  - Let errors surface clearly so tests and monitoring catch real issues early.
- Never silently swallow exceptions in new code.
- Backend:
  - validate inputs early
  - return 4xx for client errors, 5xx for server/runtime errors
  - preserve useful error detail messages where safe
- Frontend:
  - expose readable UI error state (`error.value`)
  - keep loading transitions in `finally`

## 7) Testing discipline

- Keep code, tests, and docs in sync in the same change.
- Start with targeted tests while iterating, then broaden.
- Typical backend verification order:
  1. `uv run ruff check .`
  2. `uv run black .` (or specific files)
  3. `uv run basedpyright .`
  4. targeted `uv run pytest ...`, then wider suite
- Typical frontend verification order:
  1. targeted Playwright spec(s)
  2. full `pnpm run test:e2e` for substantial UI/API changes

## 8) Rule file discovery (Cursor / Copilot)

Checked in this repository:

- `.cursor/rules/`: not found
- `.cursorrules`: not found
- `.github/copilot-instructions.md`: not found

If any of these files are added later, treat them as higher-priority instructions
and update this AGENTS.md accordingly.

## 9) Repo hygiene

- Do not commit generated runtime artifacts:
  - `frontend/test-results/`
  - `frontend/playwright-report/`
  - `frontend/dist/`
- Do not commit secrets, DSN values, or local machine-specific env data.
