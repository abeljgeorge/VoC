"""Stage 2 — Pain-point extractor (local LLM).

For each non-duplicate clean item, ask the local model for atomic pain points
and validate them against the ExtractionResult contract. Per-item failures are
dead-lettered and the batch continues (per-item failure policy, DESIGN §6.3).

Quotes are stored as returned; stage 4 enforces verbatim-ness. The prompt shows
the model the REDACTED text, so stored quotes are privacy-safe by construction.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .. import db, llm
from ..schemas import ExtractionResult

STAGE = "s2_extract"
DEPS = ["s1_clean"]
NEEDS_MODEL = llm.LOCAL_MODEL

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "s2_extract.md"
_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")
# Prompt text is part of the cache key: edit the prompt → stage re-runs (I5).
_PROMPT_VERSION = db.content_hash(_TEMPLATE)[:12]


def _rows(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT id, text_redacted FROM clean_items WHERE is_duplicate=0 ORDER BY id"
    ).fetchall()


def input_hash(conn: sqlite3.Connection) -> str:
    rows = _rows(conn)
    body = db.digest_rows((r["id"], r["text_redacted"]) for r in rows)
    return db.content_hash(body, _PROMPT_VERSION, NEEDS_MODEL)


def run(conn: sqlite3.Connection) -> dict:
    rows = _rows(conn)
    conn.execute("DELETE FROM pain_points")  # idempotent rebuild

    n_points = 0
    n_fail = 0
    for row in rows:
        item_id, text = row["id"], row["text_redacted"]
        prompt = _TEMPLATE.replace("{text}", text)  # NOT .format — prompt has literal braces
        try:
            result = llm.complete(prompt, ExtractionResult, route="local")
        except llm.LLMError as exc:
            n_fail += 1
            db.dead_letter(conn, stage=STAGE, item_id=item_id, payload=text[:500],
                           error=str(exc))
            continue

        for pp in result.pain_points:
            conn.execute(
                """INSERT OR REPLACE INTO pain_points
                   (id, item_id, issue, feature_area, severity, quote)
                   VALUES (?,?,?,?,?,?)""",
                (
                    db.content_hash(item_id, pp.issue),
                    item_id,
                    pp.issue,
                    pp.feature_area,
                    pp.severity,
                    pp.quote,
                ),
            )
            n_points += 1

    conn.commit()
    # A batch where every item failed is an infrastructure fault, not a result.
    # Raise so it is NOT cached as 'ok' and the run halts loudly (DESIGN §6.3).
    if rows and n_fail == len(rows):
        raise RuntimeError(
            f"stage 2 failed on all {n_fail} items - check the LLM backend "
            f"(first error in dead_letter table)"
        )
    return {"items": len(rows), "pain_points": n_points, "failed": n_fail}
