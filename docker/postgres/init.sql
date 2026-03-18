-- ============================================================
-- smart-home-app — PostgreSQL initialization script
-- Runs once when the postgres container is first created.
-- Alembic handles schema migrations after this point.
-- ============================================================

-- Enable UUID generation (used for primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for full-text search on audit log
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
