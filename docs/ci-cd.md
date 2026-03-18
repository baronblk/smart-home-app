# CI/CD Pipeline

## Overview

This project uses GitHub Actions for continuous integration and container releases.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** (`ci.yml`) | Push to `main`, PRs to `main` | Lint, type-check, test, Docker build |
| **Release** (`release.yml`) | Push of `v*.*.*` tag | Multi-platform build + push to GHCR |

## CI Workflow

**File:** `.github/workflows/ci.yml`

### Jobs (sequential gate)

1. **Lint** — `ruff check` + `ruff format --check`
2. **Type Check** — `mypy app/`
3. **Test** — `pytest --cov` with PostgreSQL + Redis service containers
4. **Docker Build** — Builds image (no push), runs only if lint + typecheck + test pass

### Service Containers (Test job)

| Service | Image | Port |
|---------|-------|------|
| PostgreSQL | `postgres:16` | 5432 |
| Redis | `redis:7-alpine` | 6379 |

### Environment Variables (Test job)

```
DATABASE_URL=postgresql+asyncpg://smarthome:testpassword@localhost:5432/smarthome_test
ALEMBIC_DATABASE_URL=postgresql+psycopg2://smarthome:testpassword@localhost:5432/smarthome_test
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=ci-test-secret-key-not-for-production
FRITZ_MOCK_MODE=true
PYTHONPATH=${{ github.workspace }}
```

## Release Workflow

**File:** `.github/workflows/release.yml`

### Trigger

Push a semver tag:

```bash
git tag -a v0.1.0 -m "v0.1.0 — release description"
git push origin v0.1.0
```

### What It Does

1. Logs in to GitHub Container Registry (GHCR) using `GITHUB_TOKEN`
2. Extracts metadata for image tags (semver, major.minor, latest)
3. Builds multi-platform image (`linux/amd64`, `linux/arm64`)
4. Pushes to `ghcr.io/baronblk/smart-home-app`
5. Creates a GitHub Release with auto-generated release notes

### Resulting Tags

For tag `v0.1.0`:
- `ghcr.io/baronblk/smart-home-app:0.1.0`
- `ghcr.io/baronblk/smart-home-app:0.1`
- `ghcr.io/baronblk/smart-home-app:latest`

### Required Permissions

- `contents: read` (checkout)
- `packages: write` (GHCR push)
- `contents: write` (GitHub Release creation)

No additional repository secrets needed — `GITHUB_TOKEN` is automatically provided.

## Local Verification

Before pushing, verify locally:

```bash
# Lint
ruff check app/ tests/ seeds/ scripts/
ruff format --check app/ tests/ seeds/ scripts/

# Type check
mypy app/

# Tests (requires running PostgreSQL + Redis)
PYTHONPATH=. pytest --cov=app --cov-report=xml

# Docker build
docker build -f docker/app/Dockerfile -t smart-home-app:local .
```

## Versioning Strategy

- **Semantic Versioning** (`MAJOR.MINOR.PATCH`)
- Tags follow `v0.1.0` format
- `CHANGELOG.md` tracks all notable changes per release
- Release branches are not used — releases are tagged directly on `main`
