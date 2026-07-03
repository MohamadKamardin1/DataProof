████████╗██████╗ ██╗   ██╗███████╗████████╗
╚══██╔══╝██╔══██╗██║   ██║██╔════╝╚══██╔══╝
   ██║   ██║  ██║██║   ██║█████╗     ██║
   ██║   ██║  ██║██║   ██║██╔══╝     ██║
   ██║   ██████╔╝╚██████╔╝███████╗   ██║
   ╚═╝   ╚═════╝  ╚═════╝ ╚══════╝   ╚═╝

  ██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝
  ██║  ██║██████╔╝██║   ██║██████╔╝█████╗
  ██║  ██║██╔══██╗██║   ██║██╔══██╗██╔══╝
  ██████╔╝██║  ██║╚██████╔╝██║  ██║███████╗
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝

═══════════════════════════════════════════════════════════
  TRUSTWORTHY SCIENTIFIC DATA ANALYSIS & REPORT PLATFORM
═══════════════════════════════════════════════════════════

  Turn raw tabular lab data into rigorous, LLM-narrated
  scientific reports — without ever letting AI touch your math.

═══════════════════════════════════════════════════════════

  Author:  Mohamad Kamardin
  Email:   focusinzanzibar@outlook.com
  Status:  Phase 6/6 — Production-ready
  Stack:   Python 3.12 · FastAPI · Lit 3 · PostgreSQL · Redis
  License: Proprietary — All Rights Reserved

═══════════════════════════════════════════════════════════


# WHAT IS DATAPROOF

DataProof is a scientific data analysis platform built for
researchers, labs, and field scientists. Upload CSV/XLSX
data from any instrument, map columns to semantic roles,
run deterministic analysis packs, and export a professional
PDF/DOCX report with charts, narratives, and citations.

The core guarantee: **Python computes all numbers. The LLM
only writes the story.** No AI hallucination can corrupt
your results — because the AI never touches raw data.


# THE TRUST GUARANTEE

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  1. PYTHON computes all derived values                  │
│     — deterministic, auditable, reproducible            │
│                                                         │
│  2. Analysis packs are pure functions                   │
│     — same input → same output, every time              │
│                                                         │
│  3. LLM receives ONLY pre-computed results              │
│     — never raw numbers, never file paths               │
│                                                         │
│  4. Citation validation rejects unsupported claims      │
│     — every narrative line must cite a computed value   │
│                                                         │
│  → Incorrect reports are structurally impossible.       │
│                                                         │
└─────────────────────────────────────────────────────────┘


# QUICK START

  Requires: PostgreSQL 16+, Redis 7+ (running natively)

  ┌────────────────────────────────────────────────────┐
  │  git clone git@github.com:MohamadKamardin1/        │
  │             DataProof.git                          │
  │  cd dataproof                                      │
  │  ./dev.sh                                          │
  └────────────────────────────────────────────────────┘

  ┌──────────────────────────────────┬──────────────────┐
  │ Service                          │ URL              │
  ├──────────────────────────────────┼──────────────────┤
  │ Web UI                           │ localhost:5173   │
  │ API                              │ localhost:8000   │
  │ API Docs (Swagger)               │ localhost:8000/  │
  │                                  │ docs             │
  └──────────────────────────────────┴──────────────────┘

  Then create an account at the login screen, upload a
  CSV/XLSX dataset, select an analysis pack, and generate
  your report.


# DATA PIPELINE

  UPLOAD ──▶ PARSE ──▶ SNIFF ──▶ MAPPING ──▶ ANALYZE
                                              │
                                              ▼
  EXPORT ◀── REPORT ◀── CHARTS ◀── INTERPRET ◀─┘
   PDF/              Plotly         DeepSeek
   DOCX                              LLM

  Every step is isolated. The LLM never sees raw data.
  Charts are deterministic. Citations are validated.


# FEATURES

  ┌──────────────────────────────────────────────────────┐
  │  PARSING          │  Auto-detect columns from CSV/   │
  │                   │  XLSX lab files; sniff timestamps │
  │                   │  values, units, sample IDs        │
  ├───────────────────┼──────────────────────────────────┤
  │  ANALYSIS PACKS   │  Pluggable YAML-defined packs —  │
  │                   │  paleoclimate XRF, water quality, │
  │                   │  any domain. No Python needed.    │
  ├───────────────────┼──────────────────────────────────┤
  │  VISUALIZATIONS   │  Auto-generated Plotly charts —  │
  │                   │  lines, bars, scatter, ternary,  │
  │                   │  proxy comparison grids           │
  ├───────────────────┼──────────────────────────────────┤
  │  AI NARRATIVES    │  DeepSeek-powered interpretation │
  │                   │  with executive summary, key      │
  │                   │  findings, methodology, recs      │
  ├───────────────────┼──────────────────────────────────┤
  │  EXPORT           │  Professional PDF (WeasyPrint)   │
  │                   │  and DOCX (python-docx) reports   │
  │                   │  with full citations              │
  ├───────────────────┼──────────────────────────────────┤
  │  AUTH & BILLING   │  JWT auth, workspace isolation,  │
  │                   │  Stripe billing, API keys,        │
  │                   │  plan-limit enforcement            │
  ├───────────────────┼──────────────────────────────────┤
  │  PERSISTENCE      │  All datasets, analyses, and      │
  │                   │  reports saved — return any time  │
  └───────────────────┴──────────────────────────────────┘


# TECH STACK

  ┌──────────┬───────────────────────────────────────────┐
  │ CATEGORY │ TECHNOLOGY                                │
  ├──────────┼───────────────────────────────────────────┤
  │ Backend  │ Python 3.12, FastAPI, SQLAlchemy 2.0,     │
  │          │ Alembic, Celery, Pydantic v2              │
  ├──────────┼───────────────────────────────────────────┤
  │ Frontend │ Lit 3, TypeScript 5, Vite 5, Shoelace,    │
  │          │ Plotly.js                                 │
  ├──────────┼───────────────────────────────────────────┤
  │ Database │ PostgreSQL 16, Redis 7                    │
  ├──────────┼───────────────────────────────────────────┤
  │ Storage  │ MinIO (S3-compatible) / local filesystem  │
  │          │ fallback                                  │
  ├──────────┼───────────────────────────────────────────┤
  │ AI       │ DeepSeek Chat API (report narratives)     │
  ├──────────┼───────────────────────────────────────────┤
  │ Auth     │ JWT (access + refresh), Argon2 hashing,   │
  │          │ API keys (bcrypt-style)                    │
  ├──────────┼───────────────────────────────────────────┤
  │ Billing  │ Stripe Checkout, webhooks, usage metering │
  ├──────────┼───────────────────────────────────────────┤
  │ Design   │ Brutalist UI, vintage palette, Shoelace   │
  │          │ theming, Google Fonts (Playfair Display,  │
  │          │ Space Grotesk, JetBrains Mono)             │
  └──────────┴───────────────────────────────────────────┘


# PROJECT STRUCTURE

  dataproof/
  ├── apps/
  │   ├── api/              # FastAPI backend
  │   │   ├── src/api/
  │   │   │   ├── routes/   # Endpoint modules
  │   │   │   ├── models/   # SQLAlchemy ORM models
  │   │   │   ├── templates/# HTML templates (reports)
  │   │   │   ├── packs/    # Analysis pack YAML files
  │   │   │   ├── deepseek.py
  │   │   │   ├── charting.py
  │   │   │   ├── reports.py
  │   │   │   └── s3.py
  │   │   └── alembic/      # Database migrations
  │   └── web/              # Lit + Vite frontend
  │       └── src/
  │           ├── components/  # Lit web components
  │           └── styles/      # Global CSS
  ├── docs/                  # Architecture, roadmap, ADRs
  ├── dev.sh                 # Single-command dev launcher
  └── README.md              # ← you are here


# DOCUMENTATION

  All docs live in /docs and are the source of truth:

  ┌──────────────────────────┬────────────────────────────┐
  │ File                     │ What it contains           │
  ├──────────────────────────┼────────────────────────────┤
  │ ARCHITECTURE.md          │ System design, data flow,  │
  │                          │ trust guarantee             │
  │ CONVENTIONS.md           │ Coding standards, Git       │
  │                          │ workflow                    │
  │ API_CONTRACTS.md         │ HTTP endpoint specs         │
  │ DECISIONS.md             │ ADRs (architectural         │
  │                          │ decisions)                  │
  │ ROADMAP.md               │ Phases, milestones,         │
  │                          │ acceptance criteria         │
  │ PROGRESS.md              │ Development session log     │
  │ GLOSSARY.md              │ Domain terminology          │
  └──────────────────────────┴────────────────────────────┘


# DEVELOPMENT

  ┌──────────────────────┬──────────────────────────────┐
  │ Backend              │  cd apps/api                 │
  │                      │  .venv/bin/python -m          │
  │                      │  uvicorn api.main:app         │
  │                      │  --reload                     │
  ├──────────────────────┼──────────────────────────────┤
  │ Frontend             │  cd apps/web                 │
  │                      │  npm install                  │
  │                      │  npm run dev                  │
  ├──────────────────────┼──────────────────────────────┤
  │ Tests                │  cd apps/api                 │
  │                      │  .venv/bin/python -m pytest   │
  ├──────────────────────┼──────────────────────────────┤
  │ Lint                 │  cd apps/api                 │
  │                      │  .venv/bin/python -m ruff     │
  │                      │  check .                      │
  │                      │                              │
  │                      │  cd apps/web                 │
  │                      │  npm run lint                 │
  └──────────────────────┴──────────────────────────────┘

  Or just run ./dev.sh from the root — it handles everything
  (kills stale ports, starts API + Vite, waits for health).


# STATUS

  Phase 1-6: ✅ COMPLETE (all acceptance criteria met)

  ┌──────┬──────────────────────────────────────┬────────┐
  │ PHASE│ GOAL                                 │ STATUS │
  ├──────┼──────────────────────────────────────┼────────┤
  │  1   │ Infrastructure & Scaffolding          │   ✅   │
  │  2   │ Data Ingestion (parse, sniff, map)    │   ✅   │
  │  3   │ Analysis Engine (deterministic math)  │   ✅   │
  │  4   │ LLM Interpretation (DeepSeek)         │   ✅   │
  │  5   │ Visualization & Reporting             │   ✅   │
  │  6   │ Auth, Billing & Deployment            │   ✅   │
  └──────┴──────────────────────────────────────┴────────┘


# POST-PROGRAM ROADMAP

  - OAuth2 (Google, GitHub) login
  - Kubernetes deployment
  - WebSocket real-time progress
  - More analysis pack domains
  - Rate-limiting middleware (per-plan)
  - API key auth as Bearer alternative


# BRAND

  Colors:    Rust #9B4F2E · Burnt Orange #D9733B
             Warm Sand #F5E6D3 · Deep Charcoal #1A1A1A
  Fonts:     Playfair Display (headings)
             Space Grotesk (body)
             JetBrains Mono (code)
  Vibe:      Brutalist · Scientific · Uncompromising


═══════════════════════════════════════════════════════════
  DataProof
  Built by Mohamad Kamardin · focusinzanzibar@outlook.com
  https://github.com/MohamadKamardin1/DataProof

  © 2026 Mohamad Kamardin. All rights reserved.
═══════════════════════════════════════════════════════════
