"""Central paths and constants. Keep secrets out of here — read them from env."""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = parent of the `voc` package directory.
ROOT = Path(__file__).resolve().parent.parent

# Pipeline database (git-ignored).
DB_PATH = Path(os.environ.get("VOC_DB", ROOT / "voc.db"))

# Synthetic data pack.
DATA_DIR = ROOT / "voc_synthetic_data"
TICKETS_CSV = DATA_DIR / "02_tickets" / "tickets.csv"

# Export target for the read-only dashboard (git-ignored).
EXPORT_DIR = ROOT / "exports"

# In-process model identifiers (managed by voc/models.py, one at a time — I6).
EMBED_MODEL = os.environ.get("VOC_EMBED_MODEL", "intfloat/multilingual-e5-small")
WHISPER_SIZE = os.environ.get("VOC_WHISPER_SIZE", "base")
WHISPER_COMPUTE = os.environ.get("VOC_WHISPER_COMPUTE", "int8")
