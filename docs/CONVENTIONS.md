# Conventions

This document defines the coding standards, project structure, and workflow conventions for DataProof. All contributors must follow these rules.

## Python (apps/api)

### Style & Linting

- **Formatter**: Ruff (replaces black, isort, flake8)
- **Type hints**: Mandatory for all function signatures and class attributes
- **Docstrings**: Required for public functions, classes, and modules
- **Import order**: Enforced by Ruff (stdlib → third-party → local)

### Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM", "TCH"]
ignore = []

[tool.ruff.isort]
known-first-party = ["api"]
```

### Type Hints

```python
# ✅ Good
def compute_ratio(numerator: float, denominator: float) -> float:
    ...

# ❌ Bad
def compute_ratio(numerator, denominator):
    ...
```

### Pydantic v2

**Rule: No endpoint ships without a Pydantic request/response model.**

All API I/O must use Pydantic v2 models:

```python
from pydantic import BaseModel, Field

class AnalysisRequest(BaseModel):
    project_id: int = Field(..., gt=0)
    analysis_pack: str = Field(..., min_length=1)

class AnalysisResponse(BaseModel):
    task_id: str
    status: Literal["queued", "processing", "completed"]
```

- Use `Field()` for validation constraints
- Use `ConfigDict` for model configuration
- Never use raw dicts for API responses

### Testing

**Rule: No endpoint ships without at least one test.**

- **Framework**: pytest + pytest-asyncio
- **Location**: Tests live in `apps/api/tests/` mirroring the source structure
- **Naming**: `test_<module>.py` for files, `test_<function>` for functions
- **Fixtures**: Use pytest fixtures for database sessions, test clients
- **Coverage**: Aim for >80% on new code

```
apps/api/
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_upload.py
│   └── ...
```

### Database

- **ORM**: SQLAlchemy 2.0 async with `asyncpg` driver
- **Migrations**: Alembic with auto-generated migrations
- **Naming**: Tables are plural snake_case (`measurement_results`)
- **Timestamps**: Every table has `created_at` and `updated_at` (UTC)

## TypeScript (apps/web)

### Style & Linting

- **Linter**: ESLint with TypeScript plugin
- **Formatter**: Prettier (integrated via ESLint)
- **Strict mode**: TypeScript strict mode enabled

### Component Structure (Lit 3)

```typescript
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('app-root')
export class AppRoot extends LitElement {
  @property({ type: String })
  title = 'DataProof';

  render() {
    return html`<h1>${this.title}</h1>`;
  }
}
```

### File Organization

```
apps/web/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/           # Route-level components
│   ├── services/        # API client, utilities
│   ├── types/           # TypeScript type definitions
│   ├── app-root.ts      # Root component
│   └── main.ts          # Entry point
├── public/
├── index.html
└── vite.config.ts
```

### UI Library

- **Shoelace**: Web component library for common UI patterns
- **Custom components**: Extend Shoelace, don't replace
- **Styling**: Shadow DOM with CSS (no CSS-in-JS)

## Project Structure

```
dataproof/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── src/
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── pyproject.toml
│   │   └── .env.example
│   └── web/              # Lit frontend
│       ├── src/
│       ├── public/
│       ├── package.json
│       └── vite.config.ts
├── docs/                 # Documentation (this folder)
├── .github/
│   └── workflows/
│       └── ci.yml        # CI/CD pipeline
├── docker-compose.yml
├── .gitignore
└── README.md
```

### Rules

- **No application code outside `/apps`**
- **No documentation outside `/docs`** (except README.md)
- **Shared types**: Define in `/apps/api` (Python) and mirror in `/apps/web` (TypeScript)
- **Environment files**: Commit `.env.example`, gitignore `.env`

## Git Workflow

### Commit Messages

**Format**: Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance, deps, config

**Scopes**:
- `api`: Backend changes
- `web`: Frontend changes
- `docs`: Documentation changes
- `infra`: CI/CD, Docker, config

**Examples**:
```
feat(api): add /health endpoint with database connectivity check
fix(web): correct API health indicator polling interval
docs(arch): update data flow diagram with citation validation step
chore(infra): upgrade postgres to 16.1 in docker-compose
```

### Branch Naming

```
<type>/<short-description>

feat/analysis-pack-system
fix/upload-validation-error
docs/architecture-diagram
refactor/database-models
```

### Pull Requests

- **Title**: Same as commit message format
- **Description**: Link to relevant docs, explain architectural decisions
- **Checklist**: Verify `/docs/PROGRESS.md` is updated if `/apps` changed

## Documentation Loop

**Rule: If you touch `/apps`, you must update `/docs/PROGRESS.md`.**

This is enforced by:
1. Pre-commit hook that fails if PROGRESS.md is unchanged when `/apps` is modified
2. CI check that verifies PROGRESS.md was touched in PRs affecting `/apps`

### What to Log

In `/docs/PROGRESS.md`, append a dated entry:

```markdown
## 2026-07-02

**Shipped**: /health endpoint, docker-compose setup, CI pipeline
**Known issues**: None
**Next**: Implement file upload endpoint with CSV parsing
```

## Code Review Checklist

- [ ] Pydantic models for all API endpoints
- [ ] Type hints on all functions
- [ ] At least one test per endpoint
- [ ] Ruff passes (`ruff check .`)
- [ ] pytest passes (`pytest`)
- [ ] ESLint passes (`npm run lint`)
- [ ] Vite build succeeds (`npm run build`)
- [ ] PROGRESS.md updated
- [ ] No secrets in code or commits

## Dependency Management

### Python (apps/api)

- **Tool**: uv (fast, modern Python package manager)
- **Lock file**: `uv.lock` committed to repo
- **Updates**: Monthly security audit, no auto-updates

### TypeScript (apps/web)

- **Tool**: npm
- **Lock file**: `package-lock.json` committed
- **Updates**: `npm audit` before upgrades

## Error Handling

### Python

```python
from fastapi import HTTPException

# ✅ Good: Specific exception with status code
raise HTTPException(status_code=404, detail="Project not found")

# ❌ Bad: Generic exception
raise Exception("Something went wrong")
```

### TypeScript

```typescript
// ✅ Good: Handle API errors gracefully
try {
  const response = await apiClient.get('/health');
} catch (error) {
  console.error('Health check failed:', error);
  this.apiStatus = 'unhealthy';
}
```

## Performance

- **Database**: Use `EXPLAIN ANALYZE` for complex queries
- **API**: Async endpoints for I/O-bound operations
- **Frontend**: Lazy load routes, optimize images
- **Caching**: Redis for session data, not computed results (those are deterministic)

## Security

- **Never log secrets**: Use structlog with secret filtering
- **Never commit secrets**: Pre-commit hook blocks `.env` files
- **Validate all input**: Pydantic models, not raw dicts
- **Sanitize file uploads**: Validate type, size, content
