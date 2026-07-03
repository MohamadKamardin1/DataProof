# Architecture

## System Overview

DataProof transforms raw tabular scientific data into trustworthy, LLM-narrated reports through a pipeline that strictly separates deterministic computation from generative AI interpretation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client (Lit + Vite)                             │
│                         apps/web - TypeScript + Lit 3                        │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway (FastAPI)                            │
│                          apps/api - Python 3.12                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Upload     │  │   Mapping    │  │   Analysis   │  │ Interpret    │   │
│  │   Endpoint   │  │   Endpoint   │  │   Endpoint   │  │  Endpoint    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Layer                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │    Redis     │  │    MinIO     │  │   Worker     │   │
│  │  (Metadata)  │  │   (Cache)    │  │   (Files)    │  │  (Celery)    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌────────────┐
│   Upload   │  User uploads CSV/XLSX
└─────┬──────┘
      │
      ▼
┌────────────┐
│   Parse    │  Read file, detect schema, validate structure
└─────┬──────┘
      │
      ▼
┌────────────┐
│  Sniffing  │  Auto-detect column types (timestamp, value, unit, etc.)
└─────┬──────┘
      │
      ▼
┌────────────┐
│  Mapping   │  User confirms/adjusts column mapping to semantic roles
└─────┬──────┘
      │
      ▼
┌────────────┐
│  Analysis  │  Run analysis pack: compute derived ratios, aggregations
│    Pack    │  (DETERMINISTIC PYTHON MATH - NO LLM)
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Interpret  │  Send computed results to LLM for narrative generation
│   (LLM)    │  LLM receives ONLY pre-computed facts, never raw data
└─────┬──────┘
      │
      ▼
┌────────────┐
│  Citation  │  Validate every claim in narrative cites a computed value
│ Validation │  Reject narrative if citations don't match computed results
└─────┬──────┘
      │
      ▼
┌────────────┐
│   Charts   │  Auto-generate visualizations from computed results
└─────┬──────┘
      │
      ▼
┌────────────┐
│   Report   │  Assemble PDF/DOCX with narrative + charts + citations
└─────┬──────┘
      │
      ▼
┌────────────┐
│   Export   │  User downloads final report
└────────────┘
```

## The Trust Guarantee: Why Deterministic Math is Never Delegated to LLM

**This is DataProof's core architectural principle and must never be violated.**

### The Problem

LLMs are probabilistic pattern matchers. When asked to compute ratios, averages, or derived metrics from raw numbers, they:
- Hallucinate intermediate values
- Round inconsistently
- Cannot guarantee reproducibility
- May produce plausible but incorrect arithmetic

In scientific and lab contexts, a single incorrect ratio invalidates the entire report and destroys trust.

### The Solution

DataProof enforces a **hard separation**:

1. **Python computes all math** using deterministic, auditable, tested code
2. **Analysis packs** are pure functions: `f(measurements) → derived_results`
3. **LLM receives only pre-computed results** as structured input
4. **Citation validation** ensures every narrative claim references a computed value
5. **No raw numbers are ever passed to the LLM** for computation

### Enforcement Mechanisms

- Analysis packs run in isolated Python processes with no LLM access
- LLM prompts are constructed from serialized computed results, never raw data
- Citation validator cross-references narrative claims against computed values
- Any narrative with uncited or mismatched claims is rejected and regenerated

### Why This Matters

Scientific reports must be:
- **Reproducible**: Same input → same computed results → same citations
- **Auditable**: Every claim traces to deterministic computation
- **Trustworthy**: Users can verify the math independently

If the LLM were allowed to compute ratios, none of these guarantees would hold. The architecture exists to make incorrect reports structurally impossible, not just unlikely.

## Service Responsibilities

### apps/api (FastAPI)

- HTTP endpoints for upload, mapping, analysis, interpretation, export
- Orchestration of the data pipeline
- Pydantic validation at all I/O boundaries
- Async SQLAlchemy for PostgreSQL access
- Celery task dispatch for long-running operations

### apps/web (Lit + Vite)

- Single-page application for user interaction
- File upload interface
- Column mapping UI
- Report preview and download
- Real-time status updates via polling or WebSocket (Phase 5)

### PostgreSQL

- User accounts, sessions, permissions
- Project metadata (name, created_at, status)
- Measurement schemas (column mappings)
- Analysis results (computed values, timestamps)
- Interpretation results (narratives, citations)

### Redis

- Session cache
- Celery task queue broker
- Rate limiting counters
- Temporary upload state

### MinIO (S3-compatible)

- Raw uploaded files (CSV/XLSX)
- Generated charts (PNG/SVG)
- Exported reports (PDF/DOCX)
- Intermediate artifacts

### Worker (Celery)

- File parsing and validation
- Analysis pack execution
- LLM interpretation requests
- Chart generation
- Report assembly

## Deployment Model

All services run in Docker containers.

### Development (docker-compose)

```
docker-compose.yml
├── api (FastAPI + uvicorn, hot-reload)
├── web (Vite dev server)
├── postgres (16-alpine)
├── redis (7-alpine)
├── minio (S3-compatible)
└── worker (Celery + autoreload)
```

### Production (multi-stage Docker + Fly.io / Railway)

```
api/Dockerfile (multi-stage: build → runtime)
web/Dockerfile (multi-stage: build → nginx)
```

Each service is deployed independently via GitHub Actions:
- `flyctl deploy` for API (FastAPI behind uvicorn)
- `flyctl deploy` for Web (nginx serving built Vite SPA)
- Managed Postgres, Redis, and S3 (MinIO-compatible) from the cloud provider

## Security Boundaries

- **File uploads**: Validated, size-limited, stored in MinIO with signed URLs
- **LLM calls**: Never receive raw file paths or user PII, only computed values
- **Database**: Workspace-scoped isolation via `workspace_id` foreign key on every project — enforced at the query level in every endpoint via `get_current_workspace_id` dependency
- **API**: JWT Bearer token authentication on all endpoints (except /health and /auth/*). Refresh tokens for session renewal. Argon2 password hashing.
- **API Keys**: Scoped per workspace, stored as bcrypt-style hashes, rate-limited per plan
- **Plan limits**: Free tier is enforced at the endpoint level via `enforce_plan_limit()` dependency before any expensive operation (upload, analyze, interpret, export)
- **Sentry**: Error tracking in both API and frontend

## Multi-Tenancy Model

Every user belongs to one or more **Workspaces**. Each workspace is an isolated tenant:

```
User ──< WorkspaceMembership >── Workspace ──< Project ──< Dataset
                                            └── Billing (Stripe)
```

- All projects are scoped to a workspace via `projects.workspace_id`
- All existing (Phase 2-5) endpoints have been retrofitted with workspace scoping
- The `get_current_workspace_id` dependency reads the user's `active_workspace_id` from their JWT token
- Data isolation is verified by integration tests: user A in workspace 1 cannot read workspace 2's data

## Billing Flow

```
User clicks "Upgrade" on Free tier
  → POST /api/v1/billing/checkout/{price_id}
  → Stripe Checkout session created
  → User completes payment on Stripe
  → Stripe webhook POST /api/v1/billing/webhook
  → Workspace.plan updated to "pro" or "lab"
  → Usage limits are immediately lifted (no re-login required)
```

Usage is metered via the `usage_records` table: each upload, analysis, and export creates a record. The `check_plan_limit()` function counts records in the trailing 30-day window against the plan's limits. Plan limits are defined in `PLAN_LIMITS` in `api/models/billing.py`.

## Production Topology

```
                            ┌──────────────┐
                            │   Sentry     │
                            │  (errors)    │
                            └──────┬───────┘
                                   │
┌──────────┐     HTTPS      ┌──────▼───────┐     ┌──────────────┐
│  Client   │─────────────▶  │   nginx      │────▶│   FastAPI    │
│ (Browser) │               │  (CDN/proxy) │     │  (uvicorn)   │
└──────────┘               └──────────────┘     └──────┬───────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────┐
                    │               Data Layer          │                  │
                    │  ┌──────────┐  ┌──────────┐  ┌───▼────┐  ┌────────┐ │
                    │  │PostgreSQL│  │  Redis   │  │  MinIO │  │ Worker │ │
                    │  │(primary) │  │(cache/broker)│(files) │  │(Celery)│ │
                    │  └──────────┘  └──────────┘  └────────┘  └────────┘ │
                    └──────────────────────────────────────────────────────┘
                                            │
                                   ┌────────▼────────┐
                                   │     Stripe      │
                                   │  (billing)      │
                                   └─────────────────┘
```

## Analysis Pack YAML Schema

Analysis packs are the primary extension mechanism of DataProof. Adding support for a new scientific domain (soil chemistry, water quality, ore grade, blood panels) requires **a single YAML file** — no Python code changes.

### File Location

Packs live at `/apps/api/packs/*.yaml`. They are discovered automatically on startup.

### Schema

```yaml
# Unique machine-readable identifier (snake_case)
id: domain_example

# Human-readable display name
name: Domain Example

# Description explaining the scientific domain and what the proxies mean
description: >
  Computes elemental ratios from ...

# Columns that must exist in the dataset for this pack to be compatible
required_columns:
  - Rb
  - Sr
  - Ba

# Derived ratio definitions (the core of the pack)
proxies:
  - id: rb_sr_ratio          # Machine ID (used in API responses)
    label: Rb/Sr Ratio       # Human-readable label
    formula: Rb / Sr         # Arithmetic formula (safe evaluator — see DECISIONS.md)
    unit: ratio              # Unit label for display
    description: >           # Scientific meaning of this proxy
      Chemical weathering proxy — higher values indicate stronger weathering

  - id: ba_sr_ratio
    label: Ba/Sr Ratio
    formula: Ba / Sr
    unit: ratio
    description: Paleoproductivity proxy

# Template prompt for LLM interpretation (Phase 4)
interpretation_prompt: >
  Analyze the ratios from this dataset...

# Chart type recommendations for each proxy (Phase 5)
chart_recommendations:
  - type: line              # line | bar | scatter
    title: Rb/Sr by Sample
    x_axis: sample_id
    y_axis: rb_sr_ratio
```

### Formula Language

Proxy formulas use a restricted arithmetic language processed by the safe formula evaluator (see DECISIONS.md ADR-004):

- **Variables**: column names matching `[a-zA-Z_][a-zA-Z0-9_]*`
- **Operators**: `+`, `-`, `*`, `/`
- **Grouping**: parentheses
- **Literals**: integers and floats

**Never allowed**: function calls, attribute access, indexing, string literals, imports, assignment, comparison operators.

### Creating a New Pack

1. Create `packs/<domain>.yaml` with the schema above
2. Set `required_columns` to the column names (as stored after mapping)
3. Define `proxies` with formulas referencing those columns
4. Restart the API — the pack is auto-discovered

No Python code required. The pack appears in `GET /packs` immediately.

---

## Future Considerations (Phase 2+)

- Webhook notifications for long-running analyses
- WebSocket for real-time progress updates
- Multi-tenant isolation via PostgreSQL RLS
- Horizontal scaling of worker pool
- Caching of analysis results for identical inputs
