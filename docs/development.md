# Local Development Guide

## Prerequisites

- Python 3.12+
- Docker + Docker Compose v2
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

---

## Option A: Full Docker (recommended)

The simplest way to start — everything runs in containers.

```bash
# 1. Clone and configure
git clone https://github.com/baronblk/smart-home-app.git
cd smart-home-app
cp .env.example .env
# Edit .env — set SECRET_KEY, Fritz credentials, etc.

# 2. Build and start
docker-compose up --build

# 3. Run migrations and seed (first time only)
docker-compose exec app alembic upgrade head
docker-compose exec app python seeds/run_seeds.py
```

The app is available at `http://localhost:8000`.
API docs: `http://localhost:8000/docs`

---

## Option B: Local Python + Docker services

Run the app natively with hot-reload, backed by Docker-managed DB and Redis.

```bash
# 1. Start only database and Redis
docker-compose up db redis -d

# 2. Set up Python environment
./scripts/dev_setup.sh
source .venv/bin/activate

# 3. Run migrations
alembic upgrade head

# 4. Seed database
python seeds/run_seeds.py

# 5. Start dev server
./scripts/run_dev.sh
```

---

## Environment Variables

All configuration is via environment variables. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key variables for local development:

| Variable | Recommended dev value |
|----------|-----------------------|
| `FRITZ_MOCK_MODE` | `true` (no hardware needed) |
| `ENVIRONMENT` | `development` |
| `LOG_LEVEL` | `DEBUG` |
| `SECRET_KEY` | Run `python scripts/generate_secret.py` |

---

## Running Tests

```bash
# All tests
./scripts/run_tests.sh

# Specific test file
pytest tests/unit/test_auth.py -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

Tests use the `MockProvider` — no FRITZ!Box hardware required. Tests require a PostgreSQL instance (use `docker-compose up db -d`).

---

## Code Quality

```bash
# Lint
ruff check app/ tests/

# Format
ruff format app/ tests/

# Type check
mypy app/
```

---

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration (autogenerate from models)
alembic revision --autogenerate -m "description_of_change"

# Downgrade one revision
alembic downgrade -1

# View current revision
alembic current

# Reset database (development only — destroys all data)
./scripts/db_reset.sh
```

---

## Project Layout Conventions

- **Services** (`app/<domain>/service.py`): All business logic. No raw SQL.
- **Repositories** (`app/<domain>/repository.py`): Only DB queries. No business logic.
- **Providers** (`app/providers/`): Only hardware/API access. Nothing else imports `fritzconnection`.
- **Schemas** (`app/<domain>/schemas.py`): Pydantic models for API input/output. Separate from SQLAlchemy models.
- **Models** (`app/<domain>/models.py`): SQLAlchemy ORM models only.

---

## Troubleshooting

**App won't start / migration errors:**
```bash
docker-compose logs app
docker-compose exec db pg_isready
```

**Reset everything:**
```bash
docker-compose down -v   # removes volumes too
docker-compose up --build
```
