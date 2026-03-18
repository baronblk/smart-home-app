# Architecture

## Overview

`smart-home-app` follows a layered, domain-driven architecture. The central design principle is that **all FRITZ!Box communication is isolated behind a `BaseProvider` interface**. The rest of the application only depends on this contract, never on `fritzconnection` directly.

```
┌─────────────────────────────────────────────┐
│              Web / UI Layer                  │
│   FastAPI routes · Jinja2 templates · HTMX  │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│              Service Layer                   │
│  DeviceService · SchedulerService            │
│  WeatherService · AuditService · UserService │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│            Repository Layer                  │
│   DeviceRepository · AuditRepository · …    │
│   (SQLAlchemy AsyncSession)                  │
└────────────────────┬────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │   PostgreSQL (DB)   │
          └─────────────────────┘

┌─────────────────────────────────────────────┐
│          Provider/Adapter Layer              │
│  BaseProvider (ABC)                          │
│    ├── FritzProvider → fritzconnection       │
│    └── MockProvider  → in-memory state       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│          Background Jobs (APScheduler)       │
│  poll_all_devices · evaluate_all_rules       │
│  refresh_weather_cache                       │
└─────────────────────────────────────────────┘
```

---

## Layers

### 1. Web / UI Layer (`app/api/`, `app/templates/`, `app/static/`)

FastAPI handles both JSON API requests and HTML page rendering. Routes inspect the `Accept` header: `application/json` returns a Pydantic model, `text/html` returns a `TemplateResponse`. HTMX partial requests use `HX-Request` detection for fragment responses.

### 2. Service Layer (`app/<domain>/service.py`)

Contains all business logic. Services are stateless classes instantiated via FastAPI's dependency injection. They call repositories for DB access and the provider for hardware state.

### 3. Repository Layer (`app/<domain>/repository.py`)

Thin data-access objects. Each repository holds an `AsyncSession` and exposes typed query methods. No business logic lives here.

### 4. Provider/Adapter Layer (`app/providers/`)

The critical isolation boundary. `BaseProvider` is an abstract base class defining the contract for all device operations:

```python
class BaseProvider(ABC):
    async def discover_devices(self) -> list[DeviceInfo]: ...
    async def get_device_state(self, ain: str) -> DeviceState: ...
    async def set_switch(self, ain: str, on: bool) -> None: ...
    async def set_temperature(self, ain: str, celsius: float) -> None: ...
    async def set_dimmer(self, ain: str, level: int) -> None: ...
```

`FritzProvider` implements this using `fritzconnection`. `MockProvider` uses in-memory state loaded from `tests/fixtures/fritz_mock_data.json`. The active provider is selected at startup via `settings.FRITZ_MOCK_MODE`.

**Rule: nothing outside `app/providers/` may import `fritzconnection`.**

### 5. Background Jobs (`app/scheduler/engine.py`, `app/scheduler/tasks.py`)

APScheduler `AsyncIOScheduler` runs in-process, registered in the FastAPI lifespan context. Scheduled tasks:

| Job | Interval | Purpose |
|-----|----------|---------|
| `poll_all_devices` | 60s | Sync device states to DB cache |
| `evaluate_all_rules` | 60s | Execute automation rule conditions |
| `refresh_weather_cache` | 30m | Fetch and cache weather data |

---

## Database Schema (Migrations)

| Migration | Tables |
|-----------|--------|
| `0001_initial_schema` | `users` |
| `0002_devices` | `devices`, `device_state_snapshots` |
| `0003_schedules` | `schedules`, `automation_rules` |
| `0004_audit` | `audit_events` |
| `0005_weather` | `weather_cache` |

All tables use UUID primary keys and include `created_at`/`updated_at` timestamps (via `TimestampMixin`).

---

## Authentication & RBAC

JWT-based authentication with two token types:
- **Access token**: 15 minutes, used in `Authorization: Bearer` header
- **Refresh token**: 7 days, stored in `httponly` cookie

Three roles enforced via FastAPI `Depends()`:

| Role | Capabilities |
|------|-------------|
| `admin` | Full access including user management, audit log, provider config |
| `user` | Device control, schedule management |
| `viewer` | Read-only access to dashboard and device states |

---

## Audit Log

Every state-changing operation emits an `AuditEvent` record. The `audit_events` table is **append-only** — no `UPDATE` or `DELETE` operations are permitted at the repository level. Events include: `actor_id`, `action`, `resource_type`, `resource_id`, a JSONB `payload`, `ip_address`, and `user_agent`.

Events are written via `asyncio.create_task()` — fire-and-forget, non-blocking.

---

## Architecture Decision Records

### ADR-001: FastAPI over Flask

FastAPI provides native `async/await` (essential for concurrent FRITZ!Box polling), automatic OpenAPI docs, and a built-in dependency injection system ideal for provider injection and RBAC enforcement.

### ADR-002: Jinja2 + HTMX over SPA

Avoids a Node.js build pipeline in the Docker image. HTMX partial updates provide a modern UX without full-page reloads. Alpine.js handles lightweight client-side state (modals, dropdowns).

### ADR-003: APScheduler over Celery

In-process APScheduler is sufficient for a single-instance deployment. The `SchedulerService` abstraction allows Celery to be substituted later for horizontal scaling without rewriting tasks.

### ADR-004: RBAC as enum, not table

Three static roles don't justify a `roles`/`permissions` table. A `Role` string enum column on `User` with FastAPI dependency factories is simpler, type-safe, and easy to audit.

### ADR-005: JSONB for audit payloads

Using JSONB for event payloads allows new event types to be added without schema migrations. PostgreSQL JSONB indexing supports efficient filtering.

### ADR-006: asyncpg over psycopg2

Fully non-blocking async PostgreSQL driver. Required to keep the FastAPI event loop unblocked during concurrent device state queries.
