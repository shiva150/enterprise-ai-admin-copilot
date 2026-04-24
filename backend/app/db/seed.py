"""Seed the mock SQLite database with deterministic rows.

Run: `python -m app.db.seed`

All timestamps, IDs, and messages are fixed so the same queries resolve
to the same data across runs (important for the demo and tests).
"""

from app.db import queries as _q
from app.db.schema import DROP_ALL_SQL, SCHEMA_SQL

# Original 5 users preserved (tests assert on these by id). New users added below.
USERS: list[tuple] = [
    ("U001", "Alice Lee",        "alice@example.com",   "engineer",       "active",    "2026-04-23T09:15:00"),
    ("U002", "Bob Chen",         "bob@example.com",     "intern",         "suspended", "2026-04-22T14:30:00"),
    ("U003", "Carol Davis",      "carol@example.com",   "auditor",        "active",    "2026-04-23T08:00:00"),
    ("U004", "Dave Kim",         "dave@example.com",    "support",        "active",    "2026-04-22T17:45:00"),
    ("U005", "Eve Nguyen",       "eve@example.com",     "manager",        "active",    "2026-04-20T10:00:00"),
    ("U006", "Frank Wang",       "frank@example.com",   "devops",         "active",    "2026-04-23T07:30:00"),
    ("U007", "Grace Patel",      "grace@example.com",   "security_admin", "active",    "2026-04-23T09:45:00"),
    ("U008", "Henry Oliveira",   "henry@example.com",   "engineer",       "suspended", "2026-04-19T16:00:00"),
    ("U009", "Isabella Nakamura","isabella@example.com","analyst",        "active",    "2026-04-22T13:15:00"),
    ("U010", "Jack Thompson",    "jack@example.com",    "viewer",         "active",    "2026-04-20T11:00:00"),
]

# Original 5 jobs preserved; added 5 more covering more services + failure modes.
JOBS: list[tuple] = [
    ("J001", "nightly-etl",        "failed",  "connection refused: db-primary:5432",          "2026-04-23T02:00:00"),
    ("J002", "weekly-reports",     "success", None,                                            "2026-04-22T06:00:00"),
    ("J003", "data-backup",        "running", None,                                            "2026-04-23T11:00:00"),
    ("J004", "user-sync",          "failed",  "column not found: legacy_role",                 "2026-04-23T03:30:00"),
    ("J005", "audit-export",       "success", None,                                            "2026-04-21T22:00:00"),
    ("J006", "metrics-aggregator", "success", None,                                            "2026-04-22T23:00:00"),
    ("J007", "log-rotation",       "failed",  "disk quota exceeded: /var/log at 98%",          "2026-04-23T04:15:00"),
    ("J008", "notification-queue", "running", None,                                            "2026-04-23T10:30:00"),
    ("J009", "cache-warmer",       "success", None,                                            "2026-04-23T08:00:00"),
    ("J010", "vulnerability-scan", "failed",  "timeout after 3600s on service=payments",       "2026-04-23T01:00:00"),
]

# Original 15 logs preserved (tests depend on exact counts for etl-pipeline, U002, auth-service+ERROR).
# Added 20 new logs covering new users/services. None of the additions land in
# (etl-pipeline) or (user_id=U002) or (service=auth-service AND severity=ERROR),
# so the existing log-filter tests remain untouched.
LOGS: list[tuple] = [
    # --- original 15 ---
    ("2026-04-23T08:00:00", "auth-service",     "U001", "User logged in successfully",                                "INFO"),
    ("2026-04-23T09:15:00", "auth-service",     "U001", "User session refreshed",                                      "INFO"),
    ("2026-04-22T14:30:00", "auth-service",     "U002", "User suspended by admin",                                     "WARN"),
    ("2026-04-23T10:00:00", "auth-service",     "U002", "Login attempt denied: account suspended",                     "ERROR"),
    ("2026-04-23T10:05:00", "auth-service",     "U002", "Login attempt denied: account suspended",                     "ERROR"),
    ("2026-04-23T02:00:00", "etl-pipeline",     None,   "Job nightly-etl started",                                     "INFO"),
    ("2026-04-23T02:15:00", "etl-pipeline",     None,   "Job nightly-etl failed: connection refused: db-primary:5432", "ERROR"),
    ("2026-04-23T03:30:00", "etl-pipeline",     None,   "Job user-sync failed: column not found: legacy_role",         "ERROR"),
    ("2026-04-22T06:00:00", "reporting-api",    None,   "Job weekly-reports completed",                                "INFO"),
    ("2026-04-23T11:00:00", "etl-pipeline",     None,   "Job data-backup started",                                     "INFO"),
    ("2026-04-23T09:20:00", "access-control",   "U003", "Role auditor granted access to audit_logs table",             "INFO"),
    ("2026-04-22T17:45:00", "auth-service",     "U004", "User logged in successfully",                                 "INFO"),
    ("2026-04-23T07:00:00", "auth-service",     "U001", "User session refreshed",                                      "INFO"),
    ("2026-04-23T09:30:00", "access-control",   "U002", "Role intern denied access to user_data",                      "WARN"),
    ("2026-04-20T10:00:00", "auth-service",     "U005", "User logged in successfully",                                 "INFO"),
    # --- new additions (do not touch U002 / etl-pipeline / auth-service+ERROR combo) ---
    ("2026-04-23T07:30:00", "auth-service",       "U006", "User logged in successfully",                                  "INFO"),
    ("2026-04-23T09:45:00", "auth-service",       "U007", "User logged in successfully",                                  "INFO"),
    ("2026-04-22T13:15:00", "auth-service",       "U009", "User logged in successfully",                                  "INFO"),
    ("2026-04-19T16:00:00", "auth-service",       "U008", "User session refreshed",                                        "INFO"),
    ("2026-04-23T10:12:00", "access-control",     "U008", "Account suspended by security_admin (anomaly threshold)",       "WARN"),
    ("2026-04-23T01:00:00", "security-scanner",   None,   "Vulnerability scan vulnerability-scan started",                 "INFO"),
    ("2026-04-23T02:00:00", "security-scanner",   None,   "Vulnerability scan timeout after 3600s on service=payments",    "ERROR"),
    ("2026-04-23T04:15:00", "notification-service", None, "Job log-rotation failed: disk quota exceeded",                  "ERROR"),
    ("2026-04-23T10:30:00", "notification-service", None, "Queue depth 12,483 (warn threshold=10,000)",                     "WARN"),
    ("2026-04-23T08:30:00", "reporting-api",      "U009", "Slow query: 4.2s on events table (missing index suspected)",    "WARN"),
    ("2026-04-23T08:45:00", "reporting-api",      "U009", "Query completed: 0.12s (index hit)",                             "INFO"),
    ("2026-04-22T23:00:00", "reporting-api",      None,   "Job metrics-aggregator completed in 41s",                        "INFO"),
    ("2026-04-23T08:00:00", "access-control",     "U006", "Role devops granted deploy_prod permission",                     "INFO"),
    ("2026-04-23T09:50:00", "access-control",     "U007", "Policy review completed for role=intern",                        "INFO"),
    ("2026-04-23T10:15:00", "security-scanner",   "U008", "Anomaly detected: 4 failed logins from new geolocation",         "WARN"),
    ("2026-04-23T10:16:00", "security-scanner",   "U008", "Auto-suspend triggered: severity=HIGH anomaly",                  "ERROR"),
    ("2026-04-20T11:00:00", "auth-service",       "U010", "User logged in successfully",                                    "INFO"),
    ("2026-04-23T03:00:00", "billing-service",    None,   "Invoice generation paused: missing_plan for tenant_id=T0042",    "ERROR"),
    ("2026-04-22T22:00:00", "billing-service",    None,   "Monthly invoice batch completed for 182 tenants",                "INFO"),
    ("2026-04-23T09:00:00", "access-control",     "U005", "Manager approval logged: reassign_role U009 -> analyst",         "INFO"),
]


def seed(reset: bool = True) -> None:
    _q.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _q.get_conn()
    try:
        if reset:
            conn.executescript(DROP_ALL_SQL)
        conn.executescript(SCHEMA_SQL)
        conn.executemany("INSERT INTO users VALUES (?,?,?,?,?,?)", USERS)
        conn.executemany("INSERT INTO jobs  VALUES (?,?,?,?,?)",   JOBS)
        conn.executemany(
            "INSERT INTO logs (timestamp, service, user_id, message, severity) VALUES (?,?,?,?,?)",
            LOGS,
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    seed(reset=True)
    print(f"Seeded mock DB at {_q.DB_PATH}")
    print(f"  users: {len(USERS)}, jobs: {len(JOBS)}, logs: {len(LOGS)}")


if __name__ == "__main__":
    main()
