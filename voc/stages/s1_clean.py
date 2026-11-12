"""Stage 1 — Cleaning & enrichment.

Reads `items`, writes `clean_items`: deduplicated, language-tagged, and
PII-redacted. `text_redacted` is the ONLY text the LLM is ever shown (I4).

PII redaction uses Microsoft Presidio when available and falls back to regex
for emails/phones if Presidio/spaCy isn't installed yet — so this stage runs on
day one and transparently upgrades once you `pip install` the Tier-1 extras.

Needs no model (NER backend is CPU spaCy, loaded lazily).
"""
from __future__ import annotations

import re
import sqlite3
from typing import Callable

from .. import db

STAGE = "s1_clean"
DEPS = ["s0_ingest"]
NEEDS_MODEL = None

_WS = re.compile(r"\s+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# +91 / 10-digit Indian mobile numbers, with optional spaces or dashes.
_PHONE = re.compile(r"(?:\+?91[\s-]?)?\b\d{5}[\s-]?\d{5}\b|\b\d{10}\b")


def input_hash(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT id, text FROM items").fetchall()
    return db.digest_rows((r["id"], r["text"]) for r in rows)


def run(conn: sqlite3.Connection) -> dict:
    items = conn.execute("SELECT id, text FROM items ORDER BY id").fetchall()
    detect_lang = _build_lang_detector()
    redact = _build_redactor()

    seen: dict[str, str] = {}   # normalized text -> canonical id
    out = []
    n_dupes = 0
    for row in items:
        item_id, text = row["id"], row["text"]
        norm = _WS.sub(" ", text.lower()).strip()

        canonical = seen.get(norm)
        is_dup = canonical is not None
        if is_dup:
            n_dupes += 1
        else:
            seen[norm] = item_id

        out.append(
            (item_id, redact(text), detect_lang(text), int(is_dup), canonical)
        )

    conn.execute("DELETE FROM clean_items")  # rebuild; stage is idempotent
    conn.executemany(
        """INSERT INTO clean_items (id, text_redacted, lang, is_duplicate, dup_of)
           VALUES (?,?,?,?,?)""",
        out,
    )
    conn.commit()
    return {"cleaned": len(out), "duplicates": n_dupes}


# --- Language detection -----------------------------------------------------
def _build_lang_detector() -> Callable[[str], str]:
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # deterministic

        def detect_lang(text: str) -> str:
            try:
                return detect(text)
            except Exception:
                return "unknown"

        return detect_lang
    except ImportError:
        return lambda _text: "unknown"


# --- PII redaction ----------------------------------------------------------
def _build_redactor() -> Callable[[str], str]:
    """Prefer Presidio; fall back to regex so the stage never hard-blocks."""
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        entities = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "LOCATION"]

        def redact(text: str) -> str:
            results = analyzer.analyze(text=text, language="en", entities=entities)
            return anonymizer.anonymize(text=text, analyzer_results=results).text

        print("    [s1] redactor: Presidio")
        return redact
    except Exception as exc:  # ImportError or model-load failure
        print(f"    [s1] redactor: regex fallback ({type(exc).__name__})")
        return _regex_redact


def _regex_redact(text: str) -> str:
    text = _EMAIL.sub("<EMAIL>", text)
    text = _PHONE.sub("<PHONE>", text)
    return text
