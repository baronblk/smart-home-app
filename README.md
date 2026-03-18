# smart-home-app

Production-ready, dockerized smart home web application for intelligent control of FRITZ!Box devices (thermostats, smart plugs, lights) with a clean Provider/Adapter architecture, scheduling, automation rules, weather integration, and user management.

---

## Features

- **Device Control** — Discover and control FRITZ!Box thermostats, smart plugs, and dimmable lights via the AHA protocol
- **Provider/Adapter Layer** — Clean abstraction over `fritzconnection`; a `MockProvider` enables full test coverage without hardware
- **Authentication & RBAC** — JWT-based auth with three roles: `admin`, `user`, `viewer`
- **Scheduling** — Cron/interval/date-based schedules for device actions
- **Automation Rules** — Condition-based rules (time, device state, weather triggers)
- **Weather Integration** — OpenWeatherMap cache with 30-minute refresh; usable in automation conditions
- **Audit Log** — Append-only event log for every state-changing action
- **Web UI** — Server-rendered dashboard with HTMX for live device polling and control
- **Docker-first** — Multi-stage production Dockerfile + docker-compose for local and production deployment
- **CI/CD-ready** — GitHub Actions workflows for lint, type check, tests, and GHCR publishing

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- (For local dev) Python 3.12+, PostgreSQL 16, Redis 7

### 1. Clone and configure

```bash
git clone https://github.com/baronblk/smart-home-app.git
cd smart-home-app
cp .env.example .env
# Edit .env with your FRITZ!Box credentials and secrets
```

### 2. Start with Docker

```bash
docker-compose up --build
```

The app is available at `http://localhost:8000`.
API docs: `http://localhost:8000/docs`

### 3. Run database migrations and seed

```bash
docker-compose exec app alembic upgrade head
docker-compose exec app python seeds/run_seeds.py
```

Default admin credentials are printed to the console after seeding.

### 4. Local development (without Docker)

```bash
./scripts/dev_setup.sh      # Creates venv, installs deps, copies .env
./scripts/run_dev.sh        # Starts uvicorn with --reload
```

---

## Project Structure

```
smart-home-app/
├── app/                    # Application source code
│   ├── api/v1/             # REST API endpoints
│   ├── auth/               # JWT authentication + RBAC
│   ├── providers/          # Provider/Adapter abstraction layer
│   ├── devices/            # Device domain logic
│   ├── scheduler/          # APScheduler + automation rules
│   ├── weather/            # OpenWeatherMap integration
│   ├── audit/              # Append-only audit event log
│   ├── users/              # User management
│   ├── db/                 # Database session + utilities
│   ├── models/             # SQLAlchemy base classes
│   ├── templates/          # Jinja2 HTML templates
│   └── static/             # CSS, JS, images
├── migrations/             # Alembic database migrations
├── seeds/                  # Database seed scripts
├── tests/                  # Unit and integration tests
├── docker/                 # Dockerfiles and container config
├── scripts/                # Development and operations helpers
├── docs/                   # Technical documentation
└── .github/workflows/      # CI/CD pipeline definitions
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, layer overview, key decisions |
| [docs/development.md](docs/development.md) | Local development setup guide |
| [docs/deployment.md](docs/deployment.md) | Docker production deployment |
| [docs/provider-layer.md](docs/provider-layer.md) | Provider/Adapter architecture deep-dive |
| [docs/api-reference.md](docs/api-reference.md) | REST API endpoint catalogue |
| [docs/roadmap.md](docs/roadmap.md) | Feature roadmap and milestones |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all required values. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL asyncpg DSN |
| `SECRET_KEY` | JWT signing secret (generate with `python scripts/generate_secret.py`) |
| `FRITZ_HOST` | FRITZ!Box IP or hostname |
| `FRITZ_USERNAME` | FRITZ!Box login username |
| `FRITZ_PASSWORD` | FRITZ!Box login password |
| `FRITZ_MOCK_MODE` | `true` to use MockProvider (no hardware needed) |
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap API key |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Database | PostgreSQL 16 + asyncpg |
| Background Jobs | APScheduler |
| Cache / Queue | Redis |
| Frontend | Jinja2 + HTMX + Alpine.js |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Fritz Integration | fritzconnection |
| Container | Docker (multi-stage) + docker-compose |
| Linting | Ruff |
| Type Checking | mypy |
| Testing | pytest + pytest-asyncio |

---

## License

MIT — see [LICENSE](LICENSE)
