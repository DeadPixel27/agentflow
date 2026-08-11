# AgentFlow — Engineering Principles
*Non-negotiable rules for every line of code. Reference this before every feature.*

## Why This File Exists

AI coding assistants hallucinate. They forget patterns, invent imports, skip error handling, and break layering. This document is the **source of truth** for how AgentFlow code must be written. Every PR, every feature, every refactor must follow these rules.

---

## 1. Layered Architecture — Never Skip a Layer

```
HTTP Routes (api/routes/)
    ↓ only calls
Services (services/)
    ↓ only calls
Persistence (persistence/)
    ↓ only calls
Domain Models (models/domain/)
```

### Rules

- **Routes NEVER import persistence directly.** Routes call services, services call persistence.
- **Routes NEVER contain business logic.** They validate input, call a service, map the response.
- **Services NEVER import FastAPI types** (Request, Response, HTTPException). They raise domain exceptions.
- **Persistence NEVER imports services.** Data flows down, never up.
- **Domain models are plain dataclasses.** No framework imports, no side effects, no I/O.

### Where This Applies

| Layer | Directory | Can import from | Cannot import from |
|---|---|---|---|
| Routes | `app/api/routes/` | `app/services/`, `app/models/`, `app/api/dependencies.py` | `app/persistence/` directly |
| Dependencies | `app/api/dependencies.py` | `app/persistence/`, `app/services/` | `app/api/routes/` |
| Mappers | `app/api/mappers/` | `app/models/` only | Everything else |
| Services | `app/services/` | `app/persistence/`, `app/models/`, `app/agents/` | `app/api/`, `fastapi` |
| Agents | `app/agents/` | `app/services/`, `app/models/` | `app/api/` |
| Persistence | `app/persistence/` | `app/models/domain/` only | `app/services/`, `app/api/`, `app/agents/` |
| Domain Models | `app/models/domain/` | stdlib only | Everything in `app/` |
| API Models | `app/models/api/` | stdlib, pydantic only | Everything in `app/` |

### How to Verify

If you see any of these, it's a violation:

```python
# ❌ WRONG — route importing persistence
from app.persistence import get_repository

# ✅ RIGHT — route using dependency injection
from app.api.dependencies import RepoDep

# ❌ WRONG — service raising HTTPException
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Not found")

# ✅ RIGHT — service raising domain exception
class WorkflowNotFoundError(Exception): pass
raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")

# ❌ WRONG — persistence importing service
from app.services.pipeline.planner import create_plan
# This should never happen. Data flows down only.
```

---

## 2. Domain Models — Pure Data, No Side Effects

### Rules

- Domain models live in `app/models/domain/`.
- They are **plain Python dataclasses** (or frozen dataclasses).
- They must **NOT** import FastAPI, Pydantic BaseModel, SQLAlchemy, or any framework.
- They must **NOT** have methods that do I/O (no database calls, no HTTP, no file access).
- They must **NOT** have mutable class variables or singletons.

### API Models Are Separate

- API request/response models live in `app/models/api/`.
- These **ARE** Pydantic BaseModel — they handle validation and serialization for HTTP.
- Mappers in `app/api/mappers/` convert between domain ⇔ API models.

```python
# ✅ Domain model — pure data
@dataclass
class RunResult:
    run_id: str
    status: str
    steps: list[StepRunRecord]

# ✅ API model — Pydantic, for HTTP layer only
class RunResponse(BaseModel):
    run_id: str
    status: str
    steps: list[StepRunResponse]

# ✅ Mapper — converts domain -> API
def to_run_response(run: RunResult) -> RunResponse:
    ...

# ❌ WRONG — domain model with Pydantic
from pydantic import BaseModel
class RunResult(BaseModel):  # No! Use dataclass.
    ...

# ❌ WRONG — domain model with I/O
@dataclass
class RunResult:
    def save(self):  # No! Persistence is a separate layer.
        db.insert(self)
```

---

## 3. Agent Framework — Registration Pattern

### Rules

- Every agent is a subclass of `StepHandler` with one method: `async execute(ctx, config) -> StepResult`.
- Every agent file ends with a `register_agent()` call.
- Agents self-register on import via `app/agents/handlers/__init__.py`.
- **Never hardcode agent types in the planner or runner.** Use the registry.
- The planner reads agent catalog metadata. The runner gets handler instances. They never cross.
- Agent config is a `dict[str, Any]`. Keep it flat and JSON-serializable.

### Adding a New Agent — Checklist

1. Create file in correct subfolder:
   - `handlers/processors/` — for text/OCR/input processing
   - `handlers/transforms/` — for LLM extraction, rules, calculations
   - `handlers/output/` — for formatting and delivery
2. Subclass `StepHandler`, implement `async execute()`.
3. Call `register_agent()` at module level with:
   - `agent_type` — namespaced: `category.name` (e.g., `transform.summarizer`)
   - `name` — human-readable
   - `description` — what the planner reads to decide when to use it
   - `example_config` — planner uses this to generate correct config
   - `handler` — instance of your StepHandler subclass
4. Import the new module in `handlers/__init__.py`.
5. Write a test in `tests/test_{agent_name}_agent.py`.

```python
# ❌ WRONG — hardcoded agent check in runner
if step.agent_type == "transform.field_extractor":
    handler = FieldExtractorHandler()

# ✅ RIGHT — use registry
handler = get_handler(step.agent_type)
```

---

## 4. Error Handling — Domain Exceptions, Not HTTP Exceptions

### Rules

- **Services and agents raise domain exceptions** (plain Python exceptions).
- **Routes catch domain exceptions and convert to HTTPException.**
- Every domain exception should be descriptive and include context.
- Never catch bare Exception unless you re-raise or log it.
- Never silently swallow errors.

### Exception Hierarchy

```python
# app/services/ — each service defines its own exceptions

class WorkflowNotFoundError(Exception):
    """Raised when workflow_id doesn't exist."""

class UserNotFoundError(Exception):
    """Raised when user_id doesn't exist."""

class UploadNotFoundError(Exception):
    """Raised when upload_id doesn't exist."""

class PlannerError(Exception):
    """Raised when LLM returns invalid plan."""

class AgentExecutionError(Exception):
    """Raised when a step handler fails."""
```

### Route Error Handling Pattern

```python
# ✅ RIGHT — catch specific exceptions, map to HTTP status codes
@router.post("/adhoc")
async def run_adhoc(body: RunAdhocRequest, ...):
    try:
        plan = await create_plan(body.upload_id, body.task_description)
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

```python
# ❌ WRONG — catching everything
try:
    result = do_something()
except Exception:
    pass  # Silent failure. Never do this.

# ❌ WRONG — HTTPException in a service
# services/pipeline/runner.py
from fastapi import HTTPException  # No! Services don't know about HTTP.
raise HTTPException(status_code=404, detail="Not found")
```

---

## 5. Dependency Injection — FastAPI Depends

### Rules

- All dependencies (repos, services) are injected via `Depends()` in routes.
- Use `Annotated` type aliases for clean signatures (e.g., `RepoDep`, `WorkflowServiceDep`).
- Services that run outside request cycle (e.g., BackgroundTasks) use factory functions from `app/persistence/`.
- **Never instantiate services or repositories inside route functions.**
- **Always use dependency overrides in tests** — never mock at the module level.

```python
# ✅ RIGHT — injected via Depends
@router.get("/{run_id}")
async def get_run(run_id: str, repo: RepoDep) -> RunResponse:
    run = repo.get_run(run_id)

# ❌ WRONG — direct instantiation in route
@router.get("/{run_id}")
async def get_run(run_id: str) -> RunResponse:
    repo = MemoryRepository()  # No! Use DI.
    run = repo.get_run(run_id)
```

### Test Overrides

```python
# ✅ RIGHT — override in tests
app.dependency_overrides[get_repo] = lambda: FakeRepository()
```

---

## 6. Persistence — Protocol-Based Repository Pattern

### Rules

- `protocols.py` defines interfaces (`DataRepository`, `DocumentStorageRepository`).
- Implementations (`MemoryRepository`, `SupabaseRepository`) must satisfy the protocol.
- **Never import a specific implementation outside of `persistence/`.** Always go through `get_repository()` or `get_document_store()`.
- Adding a new persistence backend = implement the protocol, register in `registry.py`. No other code changes.

```python
# ✅ RIGHT — code depends on protocol, not implementation
from app.persistence.protocols import DataRepository

def my_service(repo: DataRepository):
    repo.save_run(run)  # Works with memory, Supabase, Postgres, anything

# ❌ WRONG — code depends on specific implementation
from app.persistence.memory_repository import MemoryRepository

def my_service():
    repo = MemoryRepository()  # Tightly coupled. Can't swap backends.
```

### Adding a New Repository Method — Checklist

1. Add method signature to `protocols.py` (both `DataRepository` and/or `DocumentStorageRepository`).
2. Implement in `memory_repository.py`.
3. Implement in `supabase_repository.py`.
4. Write tests for both implementations.

---

## 7. LLM Calls — Centralized, Retryable, Validated

### Rules

- **All LLM calls go through `app/services/llm/groq_client.py`.** Never call Groq directly from agents or routes.
- Always use `response_format={"type": "json_object"}` for structured output.
- Always validate LLM output before using it (check required keys, types, values).
- Always set `temperature=0` for extraction tasks (deterministic output).
- Add retry logic with exponential backoff for transient failures (429, 503).
- Log every LLM call: model, token count, latency.
- **Never trust LLM output.** Validate agent_types, field names, config shapes.

```python
# ✅ RIGHT — validated LLM output
parsed = await complete_json(system_prompt, user_prompt)
steps = parsed.get("steps", [])
if not steps:
    raise RuntimeError("Planner returned no steps")
for step in steps:
    if not is_valid_agent_type(step.get("agent_type", "")):
        raise RuntimeError(f"Invalid agent_type: {step['agent_type']}")

# ❌ WRONG — blind trust
parsed = await complete_json(system_prompt, user_prompt)
return parsed["steps"]  # What if "steps" doesn't exist? What if agent_type is invalid?
```

---

## 8. Configuration — Single Source of Truth

### Rules

- All config lives in `app/config.py` using Pydantic `BaseSettings`.
- Settings are read from `.env` file + environment variables.
- **Never hardcode values** that might change per environment (API keys, URLs, limits, feature flags).
- Access settings via `from app.config import settings`.

```python
# ✅ RIGHT
from app.config import settings
model = settings.groq_model

# ❌ WRONG — hardcoded
model = "llama-3.3-70b-versatile"  # What if we switch models?
```

### Adding a New Config Value — Checklist

1. Add field to `Settings` class in `config.py` with a sensible default.
2. Add to `.env.example` with a comment.
3. Document in README under "Environment variables".

---

## 9. API Design — RESTful, Consistent, Predictable

### Rules

- All routes prefixed with `/api/`.
- Use plural nouns for resources: `/api/runs`, `/api/workflows`, `/api/users`.
- Use HTTP methods correctly:
  - `GET` — read (idempotent, no side effects)
  - `POST` — create or trigger action
  - `PUT` — full update
  - `PATCH` — partial update
  - `DELETE` — remove
- Return proper status codes:
  - `200` — success
  - `201` — created
  - `400` — bad request (validation error)
  - `404` — not found
  - `422` — unprocessable entity (FastAPI validation)
  - `429` — rate limited
  - `502` — upstream failure (LLM error)
- Every endpoint must have a `response_model` for type safety.
- Every POST/PUT endpoint must have a request body model (Pydantic BaseModel in `models/api/`).
- Error responses always return `{"detail": "Human-readable error message"}`.

```python
# ✅ RIGHT — consistent pattern
@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(body: WorkflowCreateRequest, ...):
    ...

# ❌ WRONG — no response model, no status code
@router.post("")
async def create_workflow(body: dict):
    ...
```

---

## 10. Async Patterns — Background Tasks for Long Operations

### Rules

- Upload + Plan = synchronous (fast, <2 seconds).
- Pipeline execution = **always background task** (can take 10-60 seconds).
- Frontend polls `GET /api/runs/{run_id}` until status is `'completed'` or `'failed'`.
- Background tasks must **save progress after each step** so polling shows real-time status.
- Background tasks must **catch all exceptions** and save error state — never leave a run in "running" forever.

```python
# ✅ RIGHT — start run synchronously, execute in background
run = await start_run(upload_id, steps)
background_tasks.add_task(execute_run, run.run_id)
return to_run_response(run)  # Returns immediately with status="running"

# ❌ WRONG — blocking the request
run = await start_run(upload_id, steps)
await execute_run(run.run_id)  # Blocks for 30+ seconds. Request times out.
return to_run_response(run)
```

---

## 11. Testing — What to Test, How to Test

### Rules

- Every agent gets a test: `tests/test_{agent}_agent.py`.
- Tests use the in-memory repository — never hit real Supabase or Groq in tests.
- Mock LLM calls with fixed JSON responses.
- Test the happy path AND at least one error path per feature.
- Use `app.dependency_overrides` to inject test doubles.
- Tests must be fast (<5 seconds total) and deterministic (no randomness, no network).

### Test Structure

```python
# tests/test_rules_agent.py

import pytest
from app.agents.core.context import WorkflowContext
from app.agents.handlers.transforms.rules import RulesHandler

@pytest.mark.asyncio
async def test_rules_flags_high_value():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"amount": 60000}, {"amount": 30000}]
    config = {"rules": [{"field": "amount", "operator": "gt", "value": 50000, "flag_name": "high_value"}]}

    handler = RulesHandler()
    result = await handler.execute(ctx, config)

    assert ctx.data["rows"][0]["flags"]["high_value"] is True
    assert "high_value" not in ctx.data["rows"][1].get("flags", {})
```

---

## 12. Security — Non-Negotiables

### Rules

- **Never log sensitive data** (API keys, user emails in production, document text).
- **Never commit `.env` files.** Use `.env.example` with placeholder values.
- **Never hardcode API keys** anywhere in the codebase.
- **Always validate file uploads** — check MIME type, file size, extension.
- **Always sanitize user input** before sending to LLM (length limits, control character stripping).
- **Always use HTTPS in production.**
- **Always set CORS origins explicitly** — never use `allow_origins=["*"]` in production.
- **Delete uploaded files after processing** (or within 24 hours) — privacy commitment.

---

## 13. Code Style — Consistency

### Rules

- **Python:** follow existing patterns in the codebase. Type hints on all function signatures.
- **TypeScript:** strict mode, no `any` unless absolutely necessary.
- **Naming:**
  - Files: `snake_case.py`, `kebab-case.tsx`
  - Classes: `PascalCase`
  - Functions/variables: `snake_case` (Python), `camelCase` (TypeScript)
  - Constants: `UPPER_SNAKE_CASE`
  - Agent types: `category.name` (e.g., `transform.field_extractor`)
- **Imports:** stdlib → third-party → local, separated by blank lines.
- **No magic numbers.** Use named constants or config values.
- **No commented-out code** in main branch. Delete it or put it behind a feature flag.

---

## 14. Git Workflow — Branch Discipline

### Rules

- `main` — production-ready, always deployable.
- `develop` — integration branch, features merge here first.
- `feature/*` — one branch per feature (e.g., `feature/template-library`).
- Commit messages: imperative mood, descriptive.
  - ✅ `"Add template registry and invoice template"`
  - ❌ `"updated stuff"`, `"wip"`, `"fix"`
- Squash merge features into develop. Merge develop into main for releases.

---

## Quick Reference — Before Writing Any Code

- [ ] Which layer does this belong in? (route / service / persistence / agent)
- [ ] Am I importing from the correct layers? (check the table in §1)
- [ ] Am I raising domain exceptions, not HTTPException? (if in service/agent)
- [ ] Am I using dependency injection, not direct instantiation? (if in route)
- [ ] Am I validating LLM output before using it?
- [ ] Am I using config values, not hardcoded strings?
- [ ] Does this need a background task? (if >2 seconds)
- [ ] Did I write at least one test?
- [ ] Did I add the new config to .env.example?
- [ ] Is user input sanitized before reaching the LLM?

---

*Transcribed from engineering-patterns screenshot session — Aug 5, 2026*
