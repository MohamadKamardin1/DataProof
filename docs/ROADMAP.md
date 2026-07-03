# Roadmap

DataProof is built in 6 phases. Each phase has clear acceptance criteria. This document is the source of truth for project status.

**Current Phase**: Phase 6 (Complete — see README.md for post-program recommendations)

---

## Phase 1: Infrastructure & Scaffolding

**Goal**: Establish the foundation — repo structure, documentation system, development environment, CI/CD pipeline.

### Acceptance Criteria

- [x] Repository structure created (`/apps/api`, `/apps/web`, `/docs`)
- [x] Documentation system established (7 files in `/docs`)
- [x] FastAPI skeleton with `/health` endpoint
- [x] Lit + Vite + TypeScript scaffold with live API health indicator
- [x] docker-compose.yml with all services (api, web, postgres, redis, minio)
- [x] GitHub Actions CI workflow (lint + test + build)
- [x] Root README.md with setup instructions
- [x] Pre-commit hook enforcing PROGRESS.md updates
- [x] `docker compose up` boots all services without errors
- [x] Web app shows live "API: healthy" indicator from real fetch
- [x] CI workflow passes on clean clone

**Status**: ✅ Complete (2026-07-02)

---

## Phase 2: Data Ingestion

**Goal**: Users can upload CSV/XLSX files, the system parses them, detects schema, and stores data in long-format measurement table.

### Acceptance Criteria

- [x] File upload endpoint accepts CSV and XLSX
- [x] File validation (type, size, structure)
- [x] Automatic schema detection (column types: timestamp, value, unit, sample_id)
- [x] Sniffing heuristics for common lab data formats
- [x] Column mapping UI for user to confirm/adjust detected schema
- [x] Data stored in long-format `measurements` table
- [x] Raw files stored in MinIO with metadata in PostgreSQL
- [x] Error handling for malformed files
- [x] Tests for upload, parsing, and validation
- [x] API_CONTRACTS.md updated with upload and mapping endpoints

**Status**: ✅ Complete (2026-07-02)

---

## Phase 3: Analysis Engine

**Goal**: Pluggable analysis pack system computes derived ratios and aggregations from measurements. All math is deterministic Python.

### Acceptance Criteria

- [x] Analysis pack plugin interface (YAML schema + Pydantic model — see ARCHITECTURE.md)
- [x] At least 2 example analysis packs implemented (paleoclimate_xrf, water_quality)
- [x] Analysis pack registry (discover, list, select from /packs directory)
- [ ] Analysis endpoint triggers async computation (Celery task) — deferred to Phase 4; synchronous sufficient for Phase 3
- [x] Computed results stored in `analysis_results` table
- [x] Results include: derived values, timestamps, citations to source measurements
- [x] Analysis packs are pure functions (no side effects, no LLM calls)
- [x] Unit tests for each analysis pack
- [x] Integration test verifying deterministic reproducibility
- [x] API_CONTRACTS.md updated with analysis endpoints

**Status**: ✅ Complete (2026-07-02)

---

## Phase 4: LLM Interpretation

**Goal**: Send computed analysis results to DeepSeek LLM for grounded narrative generation with citation validation.

### Acceptance Criteria

- [ ] LLM client (DeepSeek API integration)
- [ ] Prompt construction from computed results (never raw data)
- [ ] Narrative generation with inline citations
- [ ] Citation validator: every claim references a computed value
- [ ] Retry logic for invalid citations (regenerate narrative)
- [ ] Interpretation results stored in `interpretations` table
- [ ] Async task for LLM call (Celery)
- [ ] Rate limiting and cost tracking
- [ ] Fallback to cached interpretation on LLM failure
- [ ] API_CONTRACTS.md updated with interpretation endpoints

**Status**: 🔲 Not started

---

## Phase 5: Visualization & Reporting

**Goal**: Auto-generate charts from computed results and assemble exportable reports (PDF/DOCX) with narrative, charts, and citations.

### Acceptance Criteria

- [ ] Chart generation from analysis results (matplotlib or plotly)
- [ ] Chart types: line, bar, scatter (configurable per analysis pack)
- [ ] Charts stored in MinIO, metadata in PostgreSQL
- [ ] Report assembly: narrative + charts + citations + metadata
- [ ] PDF export (reportlab or weasyprint)
- [ ] DOCX export (python-docx)
- [ ] Report preview in web UI
- [ ] Download endpoint with signed URLs
- [ ] API_CONTRACTS.md updated with export endpoints

**Status**: 🔲 Not started

---

## Phase 6: Auth, Billing & Deployment

**Goal**: Multi-tenant SaaS with user authentication, usage-based billing, and production deployment.

### Acceptance Criteria

- [x] User registration and login (email + password, Argon2 hashing)
- [x] JWT Bearer authentication for all API endpoints (access + refresh tokens)
- [x] Workspace-scoped data isolation (workspace_id on every project query)
- [x] Usage tracking (uploads, analyses, reports_generated via usage_records table)
- [x] Billing integration (Stripe Checkout, webhooks, customer portal)
- [x] Plan-limit enforcement (free tier capped at 5 reports / 20 analyses / 10 uploads)
- [x] API keys per workspace (scoped, hashed, rate-limited per plan)
- [x] Multi-stage Docker images (api + web)
- [x] GitHub Actions deploy workflow (Fly.io)
- [x] Sentry error tracking (backend + frontend)
- [x] API_CONTRACTS.md updated with auth/billing endpoints

**Status**: ✅ Complete (2026-07-03)

### Notes

- OAuth2 (Google, GitHub) deferred — login is email+password only via `/api/v1/auth/*`
- Kubernetes deferred — Fly.io single-container deploy sufficient for SaaS launch
- Automated backups and DR procedures left to cloud provider (Fly.io Postgres)
- Stripe test mode functional — wire live keys for production
- Watermark gating now uses `workspace.plan` from Stripe subscription (not user_id==1 hack)

---

## Success Metrics

Each phase is considered complete when:

1. All acceptance criteria are checked off
2. CI/CD pipeline passes
3. Documentation is updated (ARCHITECTURE, API_CONTRACTS, PROGRESS)
4. At least one demo video or screenshot shows the feature working
5. Code review approved by at least one other engineer (or future-you)

## Principles

- **Ship incrementally**: Each phase delivers usable functionality
- **Document everything**: Future sessions depend on /docs
- **Test everything**: No feature ships without tests
- **Trust guarantee**: Never let the LLM compute numbers (ADR-002)
