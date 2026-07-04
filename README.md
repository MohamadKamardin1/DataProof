```
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
```

[![Portfolio](https://img.shields.io/badge/Portfolio-mohamadkamardin.space-9B4F2E?style=for-the-badge&logo=google-chrome&logoColor=white)](https://mohamadkamardin.space)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-%2B255778769590-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://wa.me/255778769590)
[![Email](https://img.shields.io/badge/Email-sultankvanny%40gmail.com-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:sultankvanny@gmail.com)

**Author:** Mohamad Kamardin
**Status:** Phase 6/6 — Production-ready
**Stack:** Python 3.12 · FastAPI · Lit 3 · PostgreSQL · Redis
**License:** MIT — see [LICENSE](LICENSE)

---

> **Turn raw tabular lab data into rigorous, LLM-narrated scientific
> reports — without ever letting AI touch your math.**

---

## What Is DataProof

DataProof is a scientific data analysis platform for researchers, labs, and
field scientists. Upload CSV/XLSX from any instrument, map columns to
semantic roles, run deterministic analysis packs, and export professional
PDF/DOCX reports with charts, narratives, and citations.

The core guarantee: **Python computes all numbers. The LLM only writes the
story.** No AI hallucination can corrupt your results.

---

## The Trust Guarantee

| # | Principle | Why It Matters |
|---|-----------|----------------|
| 1 | **Python computes all math** — deterministic, auditable, reproducible | Same input → same output, always |
| 2 | **Analysis packs are pure functions** — no side effects, no LLM access | Results are verifiable independently |
| 3 | **LLM receives only pre-computed results** — never raw numbers or file paths | AI cannot hallucinate a wrong ratio |
| 4 | **Citation validation** — narrative claims must reference computed values | Every line of the report is accountable |

> **→ Incorrect reports are structurally impossible to generate.**

---

## Quick Start

Requires PostgreSQL 16+ and Redis 7+ running natively.

```bash
git clone git@github.com:MohamadKamardin1/DataProof.git
cd dataproof
./dev.sh
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

Then sign up, upload a dataset, pick an analysis pack, and export your report.

---

## Data Pipeline

```
UPLOAD ──▶ PARSE ──▶ SNIFF ──▶ MAPPING ──▶ ANALYZE
                                              │
                                              ▼
EXPORT ◀── REPORT ◀── CHARTS ◀── INTERPRET ◀─┘
 PDF/              Plotly         DeepSeek
 DOCX                              LLM
```

Every step is isolated. The LLM never sees raw data. Charts are
deterministic. Citations are validated.

---

## Features

| Area | Capability |
|------|-----------|
| **Parsing** | Auto-detect columns from CSV/XLSX lab files; sniff timestamps, values, units, sample IDs |
| **Analysis Packs** | Pluggable YAML-defined packs — paleoclimate XRF, water quality, any domain. No Python needed |
| **Visualizations** | Auto-generated Plotly charts — lines, bars, scatter, ternary, proxy comparison grids |
| **AI Narratives** | DeepSeek-powered interpretation — executive summary, key findings, methodology, recommendations |
| **Export** | Professional PDF (WeasyPrint) and DOCX (python-docx) reports with full citations |
| **Auth & Billing** | JWT auth, workspace isolation, Stripe billing, API keys, plan-limit enforcement |
| **Persistence** | All datasets, analyses, and reports saved — return any time |

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Pydantic v2 |
| Frontend | Lit 3, TypeScript 5, Vite 5, Shoelace, Plotly.js |
| Database | PostgreSQL 16, Redis 7 |
| Storage | MinIO (S3-compatible) / local filesystem fallback |
| AI | DeepSeek Chat API (report narratives) |
| Auth | JWT (access + refresh), Argon2 hashing, API keys (bcrypt-style) |
| Billing | Stripe Checkout, webhooks, usage metering |
| Design | Brutalist UI, vintage palette (rust/burnt orange/warm sand), Shoelace theming |

---

## Project Structure

```
dataproof/
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── src/api/
│   │   │   ├── routes/      # Endpoint modules
│   │   │   ├── models/      # SQLAlchemy ORM models
│   │   │   ├── templates/   # HTML templates (reports)
│   │   │   ├── packs/       # Analysis pack YAML files
│   │   │   ├── deepseek.py
│   │   │   ├── charting.py
│   │   │   ├── reports.py
│   │   │   └── s3.py
│   │   └── alembic/         # Database migrations
│   └── web/                 # Lit + Vite frontend
│       └── src/
│           ├── components/  # Lit web components
│           └── styles/      # Global CSS
├── docs/                    # Architecture, roadmap, ADRs
├── dev.sh                   # Single-command dev launcher
└── README.md
```

---

## Documentation

All docs live in `/docs`:

| File | What It Contains |
|------|-----------------|
| ARCHITECTURE.md | System design, data flow, trust guarantee |
| CONVENTIONS.md | Coding standards, Git workflow |
| API_CONTRACTS.md | HTTP endpoint specifications |
| DECISIONS.md | Architectural decision records (ADRs) |
| ROADMAP.md | Phases, milestones, acceptance criteria |
| PROGRESS.md | Development session log |
| GLOSSARY.md | Domain terminology |

---

## Development

| Task | Command |
|------|---------|
| Backend | `cd apps/api && .venv/bin/python -m uvicorn api.main:app --reload` |
| Frontend | `cd apps/web && npm install && npm run dev` |
| Tests | `cd apps/api && .venv/bin/python -m pytest` |
| Lint (API) | `cd apps/api && .venv/bin/python -m ruff check .` |
| Lint (Web) | `cd apps/web && npm run lint` |

Or just run `./dev.sh` from the root — it handles everything (kills stale
ports, starts API + Vite, waits for health).

---

## Status

| Phase | Goal | Status |
|-------|------|--------|
| 1 | Infrastructure & Scaffolding | ✅ |
| 2 | Data Ingestion (parse, sniff, map) | ✅ |
| 3 | Analysis Engine (deterministic math) | ✅ |
| 4 | LLM Interpretation (DeepSeek) | ✅ |
| 5 | Visualization & Reporting | ✅ |
| 6 | Auth, Billing & Deployment | ✅ |

All 6 phases are complete. See ROADMAP.md for post-program recommendations.

---

## Post-Program Roadmap

- OAuth2 (Google, GitHub) login
- Kubernetes deployment
- WebSocket real-time progress
- More analysis pack domains
- Rate-limiting middleware (per-plan)
- API key auth as Bearer alternative

---

```
DataProof
Built by Mohamad Kamardin
```

📧 sultankvanny@gmail.com  
🌐 [mohamadkamardin.space](https://mohamadkamardin.space)  
💬 [WhatsApp: +255778769590](https://wa.me/255778769590)  
🐙 [github.com/MohamadKamardin1/DataProof](https://github.com/MohamadKamardin1/DataProof)  

MIT © 2026 Mohamad Kamardin
