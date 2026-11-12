"""SQLite layer: schema, connection, run-log and content-hash cache helpers.

Design invariants served here:
  I1/I2  counts & quotes live in their own computed tables (stage 4 fills them).
  I5     every stage is idempotent: `cache_hit()` lets the orchestrator skip a
         stage whose input_hash already has an 'ok' run_log row.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import config

# --- Schema -----------------------------------------------------------------
# One statement per table so SQLite can execute the whole script at once.
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id          TEXT PRIMARY KEY,
  source      TEXT NOT NULL,
  source_id   TEXT,
  created_at  TEXT,
  text        TEXT NOT NULL,
  lang        TEXT,
  metadata    TEXT
);

CREATE TABLE IF NOT EXISTS clean_items (
  id            TEXT PRIMARY KEY REFERENCES items(id),
  text_redacted TEXT NOT NULL,
  lang          TEXT NOT NULL,
  is_duplicate  INTEGER NOT NULL DEFAULT 0,
  dup_of        TEXT
);

CREATE TABLE IF NOT EXISTS pain_points (
  id           TEXT PRIMARY KEY,
  item_id      TEXT NOT NULL REFERENCES items(id),
  issue        TEXT NOT NULL,
  feature_area TEXT NOT NULL,
  severity     INTEGER NOT NULL,
  quote        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS themes (
  id      TEXT PRIMARY KEY,
  label   TEXT NOT NULL,
  summary TEXT
);

CREATE TABLE IF NOT EXISTS theme_members (
  theme_id      TEXT NOT NULL REFERENCES themes(id),
  pain_point_id TEXT NOT NULL REFERENCES pain_points(id),
  PRIMARY KEY (theme_id, pain_point_id)
);

CREATE TABLE IF NOT EXISTS theme_evidence (
  theme_id   TEXT PRIMARY KEY REFERENCES themes(id),
  n_mentions INTEGER NOT NULL,
  n_total    INTEGER NOT NULL,
  top_quotes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS churn_flags (
  item_id    TEXT NOT NULL REFERENCES items(id),
  flag       TEXT NOT NULL,
  method     TEXT NOT NULL,
  confidence REAL,
  PRIMARY KEY (item_id, flag)
);

CREATE TABLE IF NOT EXISTS recommendations (
  id        TEXT PRIMARY KEY,
  rank      INTEGER NOT NULL,
  title     TEXT NOT NULL,
  rationale TEXT NOT NULL,
  theme_ids TEXT NOT NULL,
  status    TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS critic_verdicts (
  rec_id     TEXT NOT NULL REFERENCES recommendations(id),
  attempt    INTEGER NOT NULL,
  verdict    TEXT NOT NULL,
  reason     TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (rec_id, attempt)
);

CREATE TABLE IF NOT EXISTS run_log (
  run_id     TEXT NOT NULL,
  stage      TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  status     TEXT NOT NULL,
  model      TEXT,
  latency_ms INTEGER,
  tokens     INTEGER,
  error      TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dead_letter (
  stage      TEXT NOT NULL,
  item_id    TEXT,
  payload    TEXT,
  error      TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_run_log_lookup ON run_log(stage, input_hash, status);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open the pipeline DB with sensible pragmas and row access by name."""
    path = Path(path) if path else config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables if absent. Safe to call every run."""
    conn.executescript(SCHEMA)
    conn.commit()


# --- Hashing / cache --------------------------------------------------------
def content_hash(*parts: object) -> str:
    """Stable sha256 over the given parts. Used for ids and cache keys (I5)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\x1f")  # unit separator so ("a","b") != ("ab",)
    return h.hexdigest()


def digest_rows(rows: Iterable[tuple]) -> str:
    """Order-independent digest of rows — a stage's input fingerprint."""
    acc = sorted(content_hash(*r) for r in rows)
    return content_hash(*acc)


def cache_hit(conn: sqlite3.Connection, stage: str, input_hash: str) -> bool:
    """True if this stage already succeeded on this exact input (I5)."""
    row = conn.execute(
        "SELECT 1 FROM run_log WHERE stage=? AND input_hash=? AND status='ok' LIMIT 1",
        (stage, input_hash),
    ).fetchone()
    return row is not None


def log_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    stage: str,
    input_hash: str,
    status: str,
    model: str | None = None,
    latency_ms: int | None = None,
    tokens: int | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO run_log
           (run_id, stage, input_hash, status, model, latency_ms, tokens, error, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (run_id, stage, input_hash, status, model, latency_ms, tokens, error, _now()),
    )
    conn.commit()


def dead_letter(
    conn: sqlite3.Connection, *, stage: str, item_id: str | None, payload: str, error: str
) -> None:
    conn.execute(
        "INSERT INTO dead_letter (stage, item_id, payload, error, created_at) VALUES (?,?,?,?,?)",
        (stage, item_id, payload, error, _now()),
    )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
