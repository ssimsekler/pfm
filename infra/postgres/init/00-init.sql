-- Runs on first DB initialization (empty data dir).
-- Creates the Keycloak schema and the read-only role used by the SQL console (Decision #10).

-- Keycloak schema (shared instance, separate schema — Decision #4)
CREATE SCHEMA IF NOT EXISTS keycloak;

-- App schema
CREATE SCHEMA IF NOT EXISTS pfm;

-- Read-only role for the guarded SQL console.
-- Password is set here from a fixed placeholder; rotate in production.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pfm_readonly') THEN
    CREATE ROLE pfm_readonly LOGIN PASSWORD 'change-me-readonly';
  END IF;
END
$$;

-- The read-only role may connect and read only. Grants on specific reporting
-- VIEWS (v_*) are applied by Alembic migrations once those views exist.
GRANT CONNECT ON DATABASE pfm TO pfm_readonly;
GRANT USAGE ON SCHEMA pfm TO pfm_readonly;

-- Ensure the read-only role cannot write.
REVOKE CREATE ON SCHEMA pfm FROM pfm_readonly;