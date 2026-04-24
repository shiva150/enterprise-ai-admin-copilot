SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('active','suspended')),
    last_login  TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id         TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('success','failed','running')),
    error_message  TEXT,
    started_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  TEXT NOT NULL,
    service    TEXT NOT NULL,
    user_id    TEXT,
    message    TEXT NOT NULL,
    severity   TEXT NOT NULL CHECK (severity IN ('INFO','WARN','ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_logs_service  ON logs(service);
CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs(severity);
CREATE INDEX IF NOT EXISTS idx_logs_user_id  ON logs(user_id);
"""

DROP_ALL_SQL = """
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS logs;
"""
