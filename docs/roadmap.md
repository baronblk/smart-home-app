# Roadmap

## Current Version: 0.1.x — Foundation

Establishes the complete repository structure, infrastructure, and architectural foundation.

- [x] Repository scaffold (Docker, docs, CI/CD preparation)
- [x] FastAPI app skeleton with health endpoint
- [x] SQLAlchemy + Alembic async database layer
- [ ] JWT authentication + RBAC (admin / user / viewer)
- [ ] Provider/Adapter abstraction (FritzProvider + MockProvider)
- [ ] Device discovery, management, and control API
- [ ] APScheduler-based scheduling and automation rules
- [ ] Jinja2 + HTMX dashboard UI
- [ ] Append-only audit event log
- [ ] OpenWeatherMap integration
- [ ] GitHub Actions CI + GHCR release workflow

---

## Planned: 0.2.x — Stability and Polish

- [ ] Unit test coverage > 80%
- [ ] Integration test coverage for all API endpoints
- [ ] Pre-commit hooks (ruff, mypy)
- [ ] Rate limiting on auth endpoints
- [ ] Pagination and filtering for all list endpoints
- [ ] Device state history charts in UI
- [ ] Email notification on automation trigger (optional)

---

## Planned: 0.3.x — Advanced Automation

- [ ] Complex rule conditions (AND/OR logic)
- [ ] Weather-based automation triggers
- [ ] Presence detection integration (based on FRITZ!Box connected devices)
- [ ] Notification channels (email, webhook)
- [ ] Automation run history and statistics

---

## Planned: 0.4.x — Multi-Provider Support

- [ ] Home Assistant provider adapter
- [ ] Tuya provider adapter (via local API)
- [ ] Multi-provider device federation

---

## Planned: 1.0.x — Production Hardening

- [ ] WebSocket push for real-time device state updates (replaces HTMX polling)
- [ ] Horizontal scaling with Celery + Redis broker
- [ ] Multi-user multi-tenant support
- [ ] Two-factor authentication
- [ ] Audit log export (CSV, JSON)
- [ ] Grafana dashboard integration
- [ ] Kubernetes deployment manifests

---

## Non-Goals

The following are explicitly out of scope for this project:

- Mobile native apps (the web UI is mobile-responsive)
- Voice assistant integration
- Z-Wave / Zigbee / Matter support (FRITZ!Box only for now)
- Cloud-hosted SaaS version
