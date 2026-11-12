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
