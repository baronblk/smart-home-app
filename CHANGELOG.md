# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Admin settings page (`/settings`) showing FRITZ!Box provider configuration,
  connection test button, and system information
- API endpoints: `GET /api/v1/settings/provider`, `POST /api/v1/settings/provider/test`,
  `GET /api/v1/settings/system` (admin-only)
- Sidebar navigation now includes Einstellungen and Profil links


---

## [0.1.1] - 2026-03-18

### Fixed
- **Container startup failure**: Added missing `psycopg[binary]` (v3) dependency.
  The app container crashed on `alembic upgrade head` with
  `ModuleNotFoundError: No module named 'psycopg'` because only `psycopg2-binary`
  was installed while the runtime used `postgresql+psycopg://`.
- Alembic env.py now converts asyncpg URLs to `postgresql+psycopg://` (modern v3)
  instead of the legacy `postgresql+psycopg2://` driver.
- Default `ALEMBIC_DATABASE_URL` in config and `.env.example` updated to use
  `postgresql+psycopg://` scheme.

### Added
- CI smoke tests verifying that DB drivers (`psycopg`, `asyncpg`, `psycopg2`)
  are importable inside the built Docker image.
- CI smoke test verifying that the app module loads successfully in the container.

---

## [0.1.0] - 2026-03-18

### Added
- Professional repository scaffold with Docker, documentation, and CI/CD preparation
- FastAPI application skeleton with health endpoint and lifespan-based startup
- SQLAlchemy 2.x async DB layer with Alembic migrations setup
- Multi-stage production Dockerfile and docker-compose orchestration
- Comprehensive project documentation (README, ARCHITECTURE, docs/)
- GitHub Actions CI pipeline and GHCR container release workflow
- JWT authentication with admin/user/viewer RBAC
- Provider/Adapter abstraction layer (FritzProvider + MockProvider)
- Device discovery, state caching, and control API
- APScheduler-based scheduling and automation rule engine
- Jinja2/HTMX dashboard with device controls and navigation
- Append-only audit event log with JSONB payloads
- OpenWeatherMap integration with 30-minute cache

---

<!-- Template for future entries:

## [0.x.0] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...

-->
