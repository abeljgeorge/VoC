"""Stage 0 — Ingestion.

Load every raw source into the unified `items` table: id, source, date, text,
metadata. For the first slice we ingest the synthetic support tickets. Audio
(Whisper) and screenshots (OCR) attach here later as additional loaders that
write the same five columns, so nothing downstream cares where text came from.

Needs no model.
"""
from __future__ import annotations

import csv
import json
import sqlite3

from .. import config

STAGE = "s0_ingest"
DEPS: list[str] = []
NEEDS_MODEL = None


def input_hash(conn: sqlite3.Connection) -> str:
    """Fingerprint = bytes of every source file we ingest."""
    from ..db import content_hash

    parts = ["tickets"]
    if config.TICKETS_CSV.exists():
        parts.append(config.TICKETS_CSV.read_bytes())
    return content_hash(*parts)


def run(conn: sqlite3.Connection) -> dict:
    n = _ingest_tickets(conn)
    conn.commit()
    return {"items_ingested": n}


def _ingest_tickets(conn: sqlite3.Connection) -> int:
    path = config.TICKETS_CSV
    if not path.exists():
        raise FileNotFoundError(f"tickets file not found: {path}")

    rows = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            source_id = _ticket_id(r.get("metadata"))
            rows.append(
                (
                    r["id"],              # already stable & unique in the dataset
                    r["source"],          # 'support_ticket'
                    source_id,
                    r["date"],
                    r["text"],
                    None,                 # lang — filled in stage 1
                    r.get("metadata"),
                )
            )

    conn.executemany(
        """INSERT OR REPLACE INTO items
           (id, source, source_id, created_at, text, lang, metadata)
           VALUES (?,?,?,?,?,?,?)""",
        rows,
    )
    return len(rows)


def _ticket_id(metadata: str | None) -> str | None:
    if not metadata:
        return None
    try:
        return json.loads(metadata).get("ticket_id")
    except (json.JSONDecodeError, AttributeError):
        return None
