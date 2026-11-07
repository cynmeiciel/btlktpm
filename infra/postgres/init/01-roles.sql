-- DEV/CI ONLY. Real passwords never live in this repo.
-- Runs automatically on first start of the postgres container (empty volume).
-- Table-level GRANTs live in the Alembic migrations, not here (docs/04-database.md §1).

CREATE ROLE s3_attendance_owner LOGIN PASSWORD 'owner-dev-pw';
CREATE ROLE s3_attendance_app   LOGIN PASSWORD 'app-dev-pw';
CREATE ROLE s4_reporting_reader LOGIN PASSWORD 'reader-dev-pw';

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA attendance AUTHORIZATION s3_attendance_owner;
GRANT USAGE ON SCHEMA attendance TO s3_attendance_app, s4_reporting_reader;
