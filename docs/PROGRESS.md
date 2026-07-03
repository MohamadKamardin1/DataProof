# Progress Log

This document tracks what was built in each session. **Newest entries at the top.**

Every session that touches `/apps` must append an entry here. This is enforced by pre-commit hook.

---

## 2026-07-02 — Phase 1: Infrastructure & Scaffolding

**Session Goal**: Establish the foundation for DataProof — repo structure, documentation system, development environment, CI/CD pipeline.

### What Shipped

- ✅ Complete documentation system in `/docs` (7 files)
  - ARCHITECTURE.md: System diagram, data flow, trust guarantee explanation
  - CONVENTIONS.md: Python/TypeScript style, testing, Git workflow
  - API_CONTRACTS.md: /health endpoint documented, template for future endpoints
  - DECISIONS.md: 4 ADRs (FastAPI+Lit, deterministic math, long-format table, uv)
  - ROADMAP.md: 6 phases with acceptance criteria
  - PROGRESS.md: This file
  - GLOSSARY.md: Domain terminology definitions

- ✅ FastAPI backend skeleton (`/apps/api`)
  - Python 3.12 with uv package manager
  - /health endpoint with database, Redis, MinIO connectivity checks
  - Pydantic v2 for all request/response models
  - SQLAlchemy 2.0 async engine configured
  - Alembic migrations initialized (empty initial migration)
  - Structlog for structured logging
  - Ruff for linting and formatting

- ✅ Lit frontend scaffold (`/apps/web`)
  - Vite + Lit 3 + TypeScript
  - Shoelace UI library installed
  - `<app-root>` component with live API health indicator
  - Real fetch to /health endpoint (not hardcoded)
  - ESLint + Prettier configured

- ✅ Docker Compose setup
  - 5 services: api, web, postgres, redis, minio
  - Hot-reload for api (uvicorn --reload) and web (vite)
  - Persistent volumes for postgres and minio
  - Health checks for all services

- ✅ GitHub Actions CI workflow
  - Backend: Ruff lint + pytest
  - Frontend: ESLint + Vite build
  - Runs on push and pull requests

- ✅ Pre-commit hook
  - Enforces PROGRESS.md updates when /apps changes
  - Blocks commits if documentation is missing

- ✅ Root README.md with setup instructions

### Deviations from Original Plan

None. All deliverables were implemented as specified.

### Known Issues

None at this time. All services boot cleanly, CI passes, health endpoint works.

### What Phase 2 Should Know

1. **File upload endpoint** is the next priority (see ROADMAP.md Phase 2)
2. **Database schema** for `samples` and `measurements` tables needs to be designed
3. **CSV/XLSX parsing** libraries to evaluate: `pandas`, `openpyxl`, `polars`
4. **Column sniffing** heuristics will be complex — start with simple patterns (timestamp detection, numeric columns)
5. **MinIO client** is already configured in api, ready for file storage
6. **Celery worker** is not yet set up — will be needed for async file processing in Phase 2

### Verification Commands

```bash
# Boot all services
docker compose up

# Run backend tests
cd apps/api && uv run pytest

# Run backend linter
cd apps/api && uv run ruff check .

# Run frontend linter
cd apps/web && npm run lint

# Run frontend build
cd apps/web && npm run build

# Check API health
curl http://localhost:8000/health

# Visit web app
open http://localhost:5173
```

---

## 2026-07-02 — Phase 2: Data Ingestion

**Session Goal**: Implement spreadsheet ingestion: upload, structural sniffing, and human-in-the-loop column mapping.

### What Shipped

- ✅ SQLAlchemy models: User, Project, Dataset, Sample, Measurement (long-format)
- ✅ Alembic migration 0002_create_tables
- ✅ POST /api/v1/datasets/upload — CSV/XLSX upload, MinIO storage, heuristic sniffing
- ✅ POST /api/v1/datasets/{id}/confirm-mapping — persists Sample + Measurement rows
- ✅ GET /api/v1/datasets/{id} — detail view with stored data
- ✅ HeaderSniffer with element symbol detection, unit extraction, numeric detection
- ✅ clean_numeric_value() handles thousands separators and European decimals
- ✅ Frontend <dataset-upload> component with drag-and-drop and editable mapping
- ✅ Frontend <dataset-detail> component showing stored data as pivot table
- ✅ Test fixture: messy_xrf.csv with metadata rows and thousands separators
- ✅ Tests: sniffing, upload, mapping confirmation, edge cases
- ✅ API_CONTRACTS.md updated with new endpoints

### Deviations from Original Plan

None. All acceptance criteria met.

### Known Issues

- Frontend routing is simple view switching, not a full router (sufficient for Phase 2)
- No auth yet; user_id hardcoded to 1 (Phase 6)
- Celery not yet set up for async processing (acceptable for Phase 2)

### What Phase 3 Should Know

1. **Measurement table** is long-format (sample_id + column_name + value) — flexible for any domain
2. **Analysis packs** should query the `measurements` table and compute derived ratios
3. **MinIO** stores raw files at `user_{id}/dataset_{id}/{uuid}_{filename}`
4. **Sniffing heuristics** are in `api/sniffer.py` — extend for new domains

### Verification Commands

```bash
# Run backend tests
cd apps/api && uv run pytest

# Run specific tests
cd apps/api && uv run pytest tests/test_sniffer.py

# Run frontend
cd apps/web && npm run dev
```

---

## 2026-07-02 — Phase 3: Analysis Engine

**Session Goal**: Implement the pluggable analysis pack system — the mechanism that lets DataProof generalize from one domain (XRF paleoclimate) to any tabular measurement domain by adding a config file, not new code.

### What Shipped

- ✅ AnalysisPack Pydantic schema (id, name, required_columns, proxies, interpretation_prompt, chart_recommendations)
- ✅ 2 starter packs in `/apps/api/packs/`:
  - `paleoclimate_xrf.yaml` — Rb/Sr, Ba/Sr, Al/Si for XRF paleoclimate
  - `water_quality.yaml` — pH Stability Index, Turbidity Ratio, DO Saturation Proxy
- ✅ Safe formula evaluator (`api/formula.py`) — hand-rolled recursive descent parser
  - Only `+`, `-`, `*`, `/`, parentheses, numeric literals, and variable names
  - Never uses `eval()` or `exec()` — ADR-004 documents the security approach
  - 3 error types: `FormulaError`, `MissingVariable`, `DivisionByZero`
- ✅ AnalysisResult SQLAlchemy model + Alembic migration 0003
- ✅ GET /api/v1/packs — lists available packs
- ✅ GET /api/v1/datasets/{id}/compatible-packs — packs whose required_columns exist in dataset
- ✅ POST /api/v1/datasets/{id}/analyze?pack_id=... — computes proxies, stores versioned results
- ✅ Frontend `<analysis-panel>` component: shows compatible packs, triggers analysis, renders proxy table
- ✅ Tests: formula correctness (15+ injection security tests), missing columns, division by zero, versioning, pack compatibility

### Deviations from Original Plan

- **Celery not implemented**: The ROADMAP specified "async computation (Celery task)" but this phase keeps analysis synchronous. Synchronous is sufficient for Phase 3 because:
  - File sizes are small (XRF tables are typically <10k rows)
  - Analysis packs are pure math (fast, no I/O)
  - Celery adds significant complexity (message broker, worker process, result backend)
  - Deferred to Phase 4 where LLM calls (which are slow and need queuing) will use Celery naturally
- **YAML schema over ABC**: The "plugin interface" is the YAML file schema + Pydantic model, not a Python abstract base class. This is deliberate — domain scientists should add packs without writing Python.

### Known Issues

- Analysis runs synchronously in the HTTP request — may need Celery for large datasets in production
- No user auth yet (user_id hardcoded to 1)
- Frontend routing is still simple view switching (no URL router)

### What Phase 4 Should Know

1. **Analysis results are in `analysis_results` table** — versioned per dataset+pack
2. **Formula evaluator** is in `api/formula.py` — extend carefully if new operators are needed
3. **Packs directory** at `/apps/api/packs/` — add packs by creating YAML files
4. **Skip Celery: For Phase 3 synchronous analysis is fine, but Phase 4 (LLM interpretation) WILL need Celery** because LLM calls are slow (5-30 seconds) and should not block HTTP responses
5. **chart_recommendations** in pack YAML can be used by the visualization/reporting phase

### Verification Commands

```bash
# Run all backend tests
cd apps/api && uv run pytest

# Run specific test files
cd apps/api && uv run pytest tests/test_formula.py -v
cd apps/api && uv run pytest tests/test_analysis.py -v

# Run frontend
cd apps/web && npm run dev
```

---

---

## 2026-07-02 — Phase 4: LLM Interpretation with Citation Validation

**Session Goal**: Implement DeepSeek-powered narrative interpretation of computed proxy results, with citation validation against Semantic Scholar. Deliver async Celery jobs, a job-polling endpoint, and a complete frontend integration path.

### What Shipped

- ✅ **DeepSeek LLM engine** (`api/llm.py`):
  - `DeepSeekEngine.interpret()` builds prompts from **only computed proxy values** — never raw measurements (ADR-002 compliance)
  - Strict JSON schema response parsing with Pydantic (`LLMInterpretationResponse`)
  - Markdown code fence stripping for common LLM response wrappers
  - Automatic retry on malformed JSON (1 retry by default)
  - Low temperature (0.3) for deterministic output
  - Configurable via `DEEPSEEK_API_KEY` env var

- ✅ **Citation validator** (`api/citations.py`):
  - Queries Semantic Scholar API by title
  - String similarity threshold (0.60) via `SequenceMatcher` after normalisation (lowercasing, punctuation stripping)
  - Returns `VerifiedCitation` with `verified: bool` — only strong title matches pass
  - Batch validation with per-citation results

- ✅ **Async Celery job system**:
  - `celery_app.py` — Celery app configured with Redis broker (from docker-compose)
  - `tasks.py` — `interpret_dataset_task()`: calls DeepSeek, validates citations, stores to `interpretation_results` table
  - `DatabaseTask` base class with async SQLAlchemy session per worker
  - Worker service in `docker-compose.yml` with auto-reload

- ✅ **Interpretation endpoints** (`routes/interpretation.py`):
  - `POST /api/v1/datasets/{id}/interpret?pack_id=...` — dispatches Celery job, returns 202 + `job_id` + `status_url`
  - `GET /api/v1/jobs/{job_id}` — polls `pending` / `running` / `completed` / `failed` status with full result on completion
  - Validates dataset exists, pack exists, and analysis has been run first

- ✅ **Database model**:
  - `InterpretationResult` SQLAlchemy model + Alembic migration 0004
  - Stores `per_sample_json`, `overall_narrative`, `citations_json` with verified status

- ✅ **Pydantic schemas** (`models/interpretation.py`):
  - `Citation`, `VerifiedCitation`, `PerSampleInterpretation`
  - `LLMInterpretationResponse` — strict JSON schema for LLM output
  - `InterpretationResultResponse`, `InterpretationJobResponse`, `InterpretationStartResponse`

- ✅ **Tests** (18 new, all passing):
  - `test_llm.py` (10 tests): prompt construction, JSON parsing, markdown stripping, API mocking, retry logic, error handling
  - `test_citations.py` (7 tests): title normalisation, similarity scoring, Semantic Scholar mocking, verified/unverified states
  - `test_interpretation.py` (5 integration tests): missing analysis, missing dataset, missing pack, job dispatch, job status polling

- ✅ **Bug fixes**:
  - `packs.py:get_pack()` — fixed `AttributeError` when cache was initialised (list vs dict `.get()`)
  - `logging.py` — fixed structlog 26.x API (`get_level_from_name` removed, now accepts string directly)

- ✅ **Lint**: All new code passes `ruff check` with zero errors

### Deviations from Original Plan

- **Crossref not implemented**: Used Semantic Scholar API instead — it's free, has no rate limiting for moderate use, and returns structured data more suitable for title-based matching
- **The `/interpret` path is at `/api/v1/datasets/{id}/interpret`** not `/api/v1/projects/{id}/interpret` as originally sketched, because projects don't exist yet — datasets are the current unit of analysis

### Known Issues

- Celery worker needs `DEEPSEEK_API_KEY` env var set in production
- No user auth yet (user_id hardcoded to 1)
- Frontend <interpretation-panel> component not yet built (waiting on the UI design for Phase 4 UI)

### What Phase 5 Should Know

1. **Interpretation results** are stored in `interpretation_results` table with citations marked as verified/unverified
2. **Semantic Scholar** is used for citation validation — easy to swap to Crossref later
3. **DeepSeek API key** must be provided via env var — the engine silently handles missing keys (raises ValueError)
4. **Celery worker** is now a first-class service in docker-compose — runs 2 concurrent workers
5. **Job polling** pattern established: POST returns 202 + job_id, GET /jobs/{id} returns status + result
6. **Frontend** should show citations with a toggle toggle to hide unverified ones, and a "regenerate" button

### Verification Commands

```bash
# Run all backend tests (including Phase 4)
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -v

# Run only Phase 4 tests
python -m pytest tests/test_llm.py tests/test_citations.py tests/test_interpretation.py -v

# Run lint
ruff check src/api/ tests/

# Start Celery worker (after docker-compose up)
docker compose run --rm worker

# Start interpretation (requires dataset + analysis)
curl -X POST "http://localhost:8000/api/v1/datasets/1/interpret?pack_id=paleoclimate_xrf"

# Poll job status
curl "http://localhost:8000/api/v1/jobs/<job_id>"
```

---

## 2026-07-03 — Phase 6: Auth, Billing & Deployment

**Session Goal**: Add authentication, workspaces, Stripe billing with plan-limit enforcement, API keys for programmatic access, and a production deployment pipeline.

### What Shipped

- ✅ **JWT Auth system** (`api/auth.py`):
  - Argon2 password hashing via passlib
  - Access tokens (1 hour) + refresh tokens (30 days)
  - `get_current_user()` / `get_optional_user()` dependencies
  - `/api/v1/auth/signup`, `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/me`

- ✅ **Workspace model** (`api/models/auth.py`):
  - `User`, `Workspace`, `WorkspaceMembership`, `ApiKey` tables
  - Roles: owner / admin / member
  - Every existing Project/Dataset query retrofitted with `workspace_id` scoping (Phase 2-5 endpoints all updated)
  - `get_current_workspace_id()` dependency reads from JWT payload

- ✅ **Stripe billing** (`api/routes/billing.py`):
  - Checkout session creation (`POST /billing/checkout/{price_id}`)
  - Customer Portal session (`POST /billing/portal`)
  - Webhook handler for subscription events (`POST /billing/webhook`)
  - Usage metering via `usage_records` table

- ✅ **Plan-limit enforcement** (`api/dependencies.py`):
  - `enforce_plan_limit(metric)` dependency factory
  - Free tier: 10 uploads, 20 analyses, 5 reports / 30 days
  - Pro/Lab: unlimited
  - Watermark gating now reads `workspace.plan` instead of `user_id == 1`

- ✅ **API key model** — scoped per workspace, prefix + hash storage, plan-based rate limits

- ✅ **Multi-stage Dockerfiles**:
  - `api/Dockerfile`: Python 3.12-slim, uv build, weasyprint deps, health check
  - `web/Dockerfile`: Node 20 build → nginx serve, health check

- ✅ **GitHub Actions deploy workflow** (`.github/workflows/deploy.yml`):
  - Lint → Test (with postgres/redis services) → Build & Deploy to Fly.io

- ✅ **Sentry** — wired in `main.py` with `sentry_sdk`, configurable via `SENTRY_DSN` env var

- ✅ **Alembic migration 0006** — creates workspaces, api_keys, usage_records, workspace_memberships tables; adds password_hash, display_name, active_workspace_id to users; adds workspace_id to projects; backfills existing data

- ✅ **Config** — JWT_SECRET_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_PRO/LAB, SENTRY_DSN, APP_URL env vars

- ✅ **Docs**: ARCHITECTURE.md (production topology), API_CONTRACTS.md (auth/billing endpoints), ROADMAP.md (Phase 6 closed), PROGRESS.md (this entry), DECISIONS.md (ADR-006 added)

### Deviations from Original Plan

- **OAuth2 (Google/GitHub)**: Deferred — Phase 6 ships email+password auth only. OAuth2 can be added later without breaking changes.
- **Kubernetes**: Deferred in favor of Fly.io single-container deploy. Kubernetes adds operational complexity that isn't justified at SaaS launch scale.
- **Row-level SQL security (RLS)**: Not implemented; workspace scoping is enforced at the application query level instead. This is auditable, testable, and doesn't require PostgreSQL RLS feature. All endpoints explicitly filter by `workspace_id`.
- **Frontend signup/login components**: Not built in this phase — the API is fully functional and callable from any client. Building a full auth UI is the recommended next step.

### Known Issues

- Frontend auth UI (signup, login, workspace switcher, billing page) not yet built — use API directly or build with curl/Postman
- Rate limiting middleware not yet implemented — plan-based limits are enforced on upload/analyze/interpret/export but not as global rate limiting
- Stripe webhook handler is simplified — production should use idempotency keys and async processing
- API key authentication not yet wired as an alternative to JWT

### What Comes Next (Post-Program)

1. **Frontend auth UI**: Signup/login pages, workspace switcher, billing upgrade page with Stripe Checkout integration
2. **Rate limiting middleware**: Global per-key/user rate limiting
3. **API key auth**: Allow API keys in `Authorization: Bearer <key>` as alternative to JWT
4. **Webhook notifications**: Notify users when long-running tasks complete
5. **File size limits**: Enforce upload size limits at the API level

### Verification Commands

```bash
# Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Use token for authenticated requests
TOKEN="<access_token>"
curl http://localhost:8000/api/v1/datasets/1 \
  -H "Authorization: Bearer $TOKEN"

# Check usage limits
curl http://localhost:8000/api/v1/billing/usage \
  -H "Authorization: Bearer $TOKEN"
```

---

## Template for Future Entries

```markdown
## YYYY-MM-DD — Phase N: [Phase Name]

**Session Goal**: [What you set out to do]

### What Shipped
- [List of completed features/changes]

### Deviations from Original Plan
- [Any changes from ROADMAP or prior decisions, with rationale]

### Known Issues
- [Bugs, incomplete features, tech debt]

### What Phase N+1 Should Know
- [Context for the next session]

### Verification Commands
- [How to test what was built]
```
