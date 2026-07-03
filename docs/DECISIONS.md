## ADR-006: Application-Level Workspace Scoping Over PostgreSQL Row-Level Security

**Date**: 2026-07-03  
**Status**: Accepted  
**Supersedes**: None

### Context

DataProof requires multi-tenant data isolation. Every project and dataset must be scoped to a workspace, and users in workspace A must never see workspace B's data. The question is where to enforce this boundary.

### Options Considered

1. **PostgreSQL Row-Level Security (RLS)**: Database-enforced, cannot be bypassed by application bugs
2. **Application-level query scoping**: Every SQL query explicitly filters by `workspace_id`
3. **Separate database per tenant**: Maximum isolation, high operational cost

### Decision

**Use application-level workspace scoping with explicit `workspace_id` filters on every query.**

### Rationale

1. **Auditability**: The scoping is visible in every endpoint's code — a code review can verify the filter is present
2. **Testability**: Workspace isolation can be tested with integration tests (user A in WS1 cannot read WS2 data)
3. **Simplicity**: No RLS policy management, no `SET session.workspace_id` per request
4. **Performance**: Indexed `workspace_id` columns perform identically to RLS policies
5. **Migration path**: If RLS is needed later, the `workspace_id` column is already in place — just add policies

### Trade-offs

- **Bug risk**: A missing `workspace_id` filter in any endpoint leaks data across tenants
- **Mitigation**: Every existing endpoint was audited and updated in this phase; new endpoints must include `get_current_workspace_id` dependency

### Consequences

- Every query joins through `Project.workspace_id` and filters by the current workspace
- The `get_current_workspace_id()` dependency is mandatory for all protected routes
- Integration tests explicitly verify cross-workspace isolation (see acceptance criteria)
- Future SQLAlchemy models must include workspace scoping from day one

---

## ADR-007: Argon2 for Password Hashing

**Date**: 2026-07-03  
**Status**: Accepted  
**Supersedes**: None

### Context

DataProof stores user passwords and needs a secure hashing algorithm. The choice affects resistance to offline brute-force attacks and login latency.

### Options Considered

1. **bcrypt**: Industry standard, well-audited, moderate resistance
2. **Argon2id**: Modern, memory-hard, resistant to GPU/ASIC attacks
3. **scrypt**: Memory-hard, widely supported

### Decision

**Use Argon2id via passlib** — the current NIST-recommended password hashing algorithm.

### Rationale

- Argon2id is resistant to GPU, ASIC, and side-channel attacks
- Configurable time/memory/parallelism costs
- Passlib provides a well-tested wrapper with automatic salt
- Default parameters (t=3, m=65536, p=4) provide strong protection at ~50ms verification time

---

## ADR-008: Stripe Over Other Billing Providers

**Date**: 2026-07-03  
**Status**: Accepted  
**Supersedes**: None

### Context

DataProof needs subscription billing with free/pro/lab tiers, usage metering, and customer self-service.

### Options Considered

1. **Stripe**: Mature API, Checkout, Customer Portal, webhooks, test mode
2. **Paddle**: Complete merchant of record, handles VAT/sales tax
3. **Lemon Squeezy**: Modern, built for SaaS, merchant of record

### Decision

**Use Stripe** for billing.

### Rationale

- **Development speed**: Stripe Checkout provides a hosted payment page with zero frontend work
- **Customer Portal**: Users can manage subscriptions, invoices, and payment methods without custom UI
- **Test mode**: Complete sandbox for development and testing
- **Webhook reliability**: Built-in retry and idempotency
- **Precedent**: Stripe is the most widely integrated billing provider; team familiarity is high

### Trade-offs

- Stripe is not a merchant of record — the seller (DataProof) is responsible for tax compliance
- Paddle/Lemon Squeezy handle VAT automatically, Stripe requires separate tax handling

---

