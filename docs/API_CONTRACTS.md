# API Contracts

This document defines all HTTP API endpoints for DataProof. Every endpoint must be documented here before implementation.

## Documentation Format

Each endpoint is documented using this table format:

| Field            | Value                          |
|------------------|--------------------------------|
| **Method**       | GET / POST / PUT / DELETE      |
| **Path**         | /api/v1/...                    |
| **Auth**         | None / Bearer / Session        |
| **Request**      | Pydantic model or query params |
| **Response**     | Pydantic model                 |
| **Error Codes**  | 400, 401, 404, 500             |

## Endpoints

### Health Check

| Field            | Value                                                                 |
|------------------|-----------------------------------------------------------------------|
| **Method**       | GET                                                                   |
| **Path**         | /health                                                               |
| **Auth**         | None                                                                  |
| **Request**      | None                                                                  |
| **Response**     | `HealthResponse` (see below)                                          |
| **Error Codes**  | 503 (service unavailable)                                             |

#### Response Schema

```python
class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
    checks: dict[str, bool]  # {"database": True, "redis": True, "minio": True}
```

#### Example Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-07-02T12:00:00Z",
  "checks": {
    "database": true,
    "redis": true,
    "minio": true
  }
}
```

#### Behavior

- Returns 200 if all checks pass
- Returns 503 if any critical check fails (database, redis)
- `checks.minio` failure degrades status to "degraded" but still returns 200
- Used by load balancers, monitoring, and frontend health indicator

#### Implementation Notes

- Check database connectivity with a simple `SELECT 1`
- Check Redis with `PING`
- Check MinIO with bucket existence check
- Timeout each check at 2 seconds
- Cache results for 30 seconds to avoid hammering dependencies

---

### Dataset Upload

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/datasets/upload                  |
| **Auth**         | Bearer                                                                  |
| **Request**      | `multipart/form-data` with file          |
| **Response**     | `UploadResponse`                         |
| **Error Codes**  | 400 (invalid file), 401 (unauthorized), 403 (plan limit), 413 (too large)|

#### Response Schema

```python
class UploadResponse(BaseModel):
    dataset_id: int
    name: str
    status: str
    detected_schema: list[ColumnMapping]
    s3_key: str

class ColumnMapping(BaseModel):
    name: str
    role: Literal["sample_id", "measurement", "ignore"]
    confidence: float
    unit: str | None = None
    data_type: str | None = None
```

#### Behavior

- Accepts CSV and XLSX files
- Parses file and detects column types using heuristic sniffing
- Stores raw file in MinIO under `user_{id}/dataset_{id}/{uuid}_{filename}`
- Returns detected schema with confidence scores for each column
- Heuristic: element symbols (Rb, Sr, Ba, etc.), unit patterns in headers, numeric percentage

---

### Confirm Column Mapping

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/datasets/{id}/confirm-mapping    |
| **Auth**         | Bearer                                                                   |
| **Request**      | `ConfirmMappingRequest`                  |
| **Response**     | `ConfirmMappingResponse`                 |
| **Error Codes**  | 400 (invalid mapping), 401 (unauthorized), 404 (not found), 409 (already mapped) |

#### Request Schema

```python
class ConfirmMappingRequest(BaseModel):
    mappings: list[ColumnMapping]
```

#### Response Schema

```python
class ConfirmMappingResponse(BaseModel):
    dataset_id: int
    status: str
    samples_stored: int
    measurements_stored: int
```

#### Behavior

- Validates that exactly one `sample_id` column is selected
- Persists Sample and Measurement rows to PostgreSQL
- Measurements stored in long-format (sample_id + column_name + value)
- Dataset status changes from "uploaded" to "mapped"

---

### Get Dataset Detail

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | GET                                      |
| **Path**         | /api/v1/datasets/{id}                    |
| **Auth**         | Bearer                                   |
| **Request**      | None                                     |
| **Response**     | `DatasetDetailResponse`                  |
| **Error Codes**  | 404 (not found)                          |

#### Response Schema

```python
class DatasetDetailResponse(BaseModel):
    dataset_id: int
    name: str
    status: str
    columns: list[str]
    rows: list[dict[str, str | float | None]]
```

#### Behavior

- Returns the stored data (not the raw upload) as actually stored in the database
- Used as a regression check for the whole pipeline
- Pivot from long-format measurements to wide-format for display

---

---

### List Analysis Packs

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | GET                                      |
| **Path**         | /api/v1/packs                            |
| **Auth**         | Bearer                                   |
| **Request**      | None                                     |
| **Response**     | `list[PackSummary]`                      |
| **Error Codes**  | None                                     |

#### Response Schema

```python
class PackSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    required_columns: list[str]
```

### List Compatible Packs for Dataset

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | GET                                      |
| **Path**         | /api/v1/datasets/{id}/compatible-packs   |
| **Auth**         | Bearer                                   |
| **Request**      | None                                     |
| **Response**     | `list[PackSummary]`                      |
| **Error Codes**  | 404 (dataset not found)                  |

#### Behavior

- Returns only packs whose `required_columns` are all present in the dataset's stored measurements
- Frontend uses this to show the user which packs they can run

### Run Analysis

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/datasets/{id}/analyze            |
| **Auth**         | Bearer                                   |
| **Request**      | Query param `pack_id` (default: paleoclimate_xrf) |
| **Response**     | `AnalysisResponse`                       |
| **Error Codes**  | 400 (no measurements), 404 (not found)   |

#### Response Schema

```python
class ProxyResult(BaseModel):
    proxy_id: str
    label: str
    sample_id: str
    value: float | None   # null if division by zero or missing column
    unit: str | None

class AnalysisResponse(BaseModel):
    dataset_id: int
    pack: str
    version: int           # incremented on each re-analysis
    results: list[ProxyResult]
```

#### Behavior

- Computes every proxy defined in the pack for every sample in the dataset
- Results are versioned — re-running creates version 2, both versions are stored
- Division by zero or missing columns yield `null` for that specific proxy/sample combo
- All math is deterministic Python; the LLM never touches formulas

---

## Phase 4 Endpoints

### Start Interpretation (Async Job)

| Field            | Value                                      |
|------------------|--------------------------------------------|
| **Method**       | POST                                       |
| **Path**         | /api/v1/datasets/{id}/interpret            |
| **Auth**         | None (Phase 6: Bearer)                     |
| **Request**      | Query param `pack_id` (default: paleoclimate_xrf) |
| **Response**     | `InterpretationStartResponse` (HTTP 202)   |
| **Error Codes**  | 400 (no analysis), 404 (dataset/pack not found) |

#### Response Schema

```python
class InterpretationStartResponse(BaseModel):
    job_id: str
    status_url: str  # /api/v1/jobs/{job_id}
```

#### Behavior

- Requires analysis results to exist (run `/analyze` first)
- Dispatches Celery task to call DeepSeek API with computed proxy results only
- Returns 202 Accepted with a `job_id` for polling
- Never sends raw measurements to the LLM (ADR-002)

---

### Poll Interpretation Job Status

| Field            | Value                                      |
|------------------|--------------------------------------------|
| **Method**       | GET                                        |
| **Path**         | /api/v1/jobs/{job_id}                      |
| **Auth**         | None (Phase 6: Bearer)                     |
| **Request**      | None                                       |
| **Response**     | `InterpretationJobResponse`                |
| **Error Codes**  | None (returns status even for unknown jobs)|

#### Response Schema

```python
class VerifiedCitation(BaseModel):
    authors: str
    year: int | None = None
    title: str
    venue: str | None = None
    doi_or_url: str | None = None
    verified: bool

class PerSampleInterpretation(BaseModel):
    sample_id: str
    classification: str
    rationale: str

class InterpretationResultResponse(BaseModel):
    per_sample: list[PerSampleInterpretation]
    overall_narrative: str
    citations: list[VerifiedCitation]

class InterpretationJobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: InterpretationResultResponse | None = None
    error: str | None = None
```

#### Behavior

- Poll until status is "completed" or "failed"
- Citations are validated against Semantic Scholar — each has a `verified: bool`
- Unverified citations have `verified=False` but are still included
- Failed jobs return `error` field with the exception message

---

### Export

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/projects/{id}/export             |
| **Auth**         | Bearer (Phase 6)                         |
| **Request**      | `ExportRequest`                          |
| **Response**     | `ExportResponse` (download URL)          |
| **Error Codes**  | 400 (no interpretation), 404 (not found) |

## Versioning

- All endpoints are prefixed with `/api/v1/` (except `/health`)
- Breaking changes require a new version (v2)
- Additive changes (new optional fields) do not require versioning

## Authentication

All endpoints except `/health` and `/api/v1/auth/*` require a JWT Bearer token via the `Authorization: Bearer <token>` header.

### Auth Endpoints

#### POST /api/v1/auth/signup

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/auth/signup                      |
| **Auth**         | None                                     |
| **Request**      | `SignupRequest`                          |
| **Response**     | `TokenResponse` (201)                    |

```python
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = None
    workspace_name: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    workspace_id: int | None = None
```

#### POST /api/v1/auth/login

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/auth/login                       |
| **Auth**         | None                                     |
| **Request**      | `LoginRequest`                           |
| **Response**     | `TokenResponse`                          |

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

#### POST /api/v1/auth/refresh

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | POST                                     |
| **Path**         | /api/v1/auth/refresh                     |
| **Auth**         | None (uses refresh_token in body)        |
| **Request**      | `RefreshRequest`                         |
| **Response**     | `TokenResponse`                          |

#### GET /api/v1/auth/me

| Field            | Value                                    |
|------------------|------------------------------------------|
| **Method**       | GET                                      |
| **Path**         | /api/v1/auth/me                          |
| **Auth**         | Bearer                                   |
| **Response**     | `UserResponse`                           |

### Billing Endpoints

#### POST /api/v1/billing/checkout/{price_id}

Creates a Stripe Checkout session for subscription upgrade.

#### POST /api/v1/billing/portal

Creates a Stripe Customer Portal session for managing the subscription.

#### GET /api/v1/billing/usage

Returns the current workspace's plan limits and usage.

#### POST /api/v1/billing/webhook

Stripe webhook endpoint (public, validated via signature).

### Workspace Endpoints

#### GET /api/v1/workspaces/

List workspaces for the current user.

#### POST /api/v1/workspaces/

Create a new workspace.

#### POST /api/v1/workspaces/{id}/switch

Set the user's active workspace.

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2026-07-02T12:00:00Z"
}
```

### Common Error Codes

| HTTP Status | Error Code              | Description                          |
|-------------|-------------------------|--------------------------------------|
| 400         | INVALID_REQUEST         | Malformed request body or params     |
| 401         | UNAUTHORIZED            | Missing or invalid auth token        |
| 403         | FORBIDDEN               | Insufficient permissions             |
| 404         | NOT_FOUND               | Resource does not exist              |
| 409         | CONFLICT                | Resource state conflict              |
| 413         | FILE_TOO_LARGE          | Upload exceeds size limit            |
| 422         | UNPROCESSABLE_ENTITY    | Validation failed                    |
| 500         | INTERNAL_ERROR          | Unexpected server error              |
| 503         | SERVICE_UNAVAILABLE     | Dependency unavailable               |

## Rate Limiting

Rate limits are enforced per API key / user based on the workspace's plan:
- **Free**: 30 requests/minute
- **Pro**: 300 requests/minute
- **Lab**: 1000 requests/minute

Exceeding the limit returns HTTP 429.

## CORS

- **Development**: Allow `http://localhost:5173` (Vite dev server), `http://localhost:4173` (Vite preview)
- **Production**: Restrict to the application's domain
