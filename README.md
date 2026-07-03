# DataProof

Scientific data analysis and interpretation platform that transforms tabular lab data into trustworthy, LLM-narrated reports.

## Quick Start

```bash
docker compose up
```

Then visit:
- **Web UI**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001

## Development

### Prerequisites

- Docker and Docker Compose
- Git

### Running Locally

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd dataproof
   ```

2. Start all services:
   ```bash
   docker compose up
   ```

3. The web app will show a live "API: healthy" indicator sourced from the backend.

### Backend Development

```bash
cd apps/api
uv sync
uv run uvicorn api.main:app --reload
```

Run tests:
```bash
uv run pytest
```

Lint:
```bash
uv run ruff check .
```

### Frontend Development

```bash
cd apps/web
npm install
npm run dev
```

Build:
```bash
npm run build
```

Lint:
```bash
npm run lint
```

## Documentation

The `/docs` directory contains comprehensive documentation:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design, data flow, and the trust guarantee
- **[CONVENTIONS.md](docs/CONVENTIONS.md)** — Coding standards, project structure, Git workflow
- **[API_CONTRACTS.md](docs/API_CONTRACTS.md)** — HTTP API endpoint specifications
- **[DECISIONS.md](docs/DECISIONS.md)** — Architectural decision records (ADRs)
- **[ROADMAP.md](docs/ROADMAP.md)** — Project phases and acceptance criteria (source of truth for status)
- **[PROGRESS.md](docs/PROGRESS.md)** — Session-by-session development log
- **[GLOSSARY.md](docs/GLOSSARY.md)** — Domain terminology

**Read these before contributing.** Future sessions depend on this documentation.

## Project Status

See **[ROADMAP.md](docs/ROADMAP.md)** for current phase and acceptance criteria.

**Current Phase**: Phase 6 (Auth, Billing & Deployment) — Complete

> **Note**: All 6 phases are now complete. Next steps include frontend auth UI, rate limiting middleware, and API key auth. See [ROADMAP.md](docs/ROADMAP.md) for post-program recommendations.

## Architecture

DataProof enforces a hard separation between deterministic computation (Python) and LLM narrative generation. This is the core trust guarantee: **the LLM never computes numbers, only interprets pre-computed results**.

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

## License

Proprietary. All rights reserved.
