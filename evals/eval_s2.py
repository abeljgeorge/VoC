"""Eval — Stage 2 pain-point extraction vs tickets_groundtruth.csv.

Reports, with code (never the model) doing the counting:
  - feature-area precision / recall / F1, matched at the (item_id, area) grain
  - per-area recall breakdown (failure analysis)
  - quote faithfulness: share of predicted quotes found verbatim in the text
  - severity accuracy on matched pairs
  - non-pain precision: do the 20 praise/question/request items stay empty?

Run AFTER stage 2 has populated `pain_points`:
    python -m evals.eval_s2
    python evals/eval_s2.py          # also works (self-adds repo root to path)
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow running as a plain script, not only `python -m`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voc import config, db  # noqa: E402

GROUND_TRUTH = config.DATA_DIR / "02_tickets" / "tickets_groundtruth.csv"


def load_ground_truth():
    """Return gt_pairs {(item_id, area)}, gt_sev {(item_id,area): severity},
    and nonpain_items {item_id with zero pain points}."""
    gt_pairs: set[tuple[str, str]] = set()
    gt_sev: dict[tuple[str, str], str] = {}
    nonpain: set[str] = set()
    with GROUND_TRUTH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pps = json.loads(row["pain_points_json"]) if row["pain_points_json"] else []
            if not pps:
                nonpain.add(row["id"])
            for p in pps:
                key = (row["id"], p["feature_area"])
                gt_pairs.add(key)
                gt_sev.setdefault(key, p.get("severity", ""))
    return gt_pairs, gt_sev, nonpain


def load_predictions(conn):
    """Predicted (item_id, area) pairs, their severities, and the raw rows."""
    rows = conn.execute(
        "SELECT item_id, feature_area, severity, quote FROM pain_points"
    ).fetchall()
    pred_pairs: set[tuple[str, str]] = set()
    pred_sev: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["item_id"], r["feature_area"])
        pred_pairs.add(key)
        pred_sev.setdefault(key, r["severity"])
    return pred_pairs, pred_sev, rows


def quote_faithfulness(conn, rows) -> tuple[int, int]:
    """Count quotes found verbatim in the text the model saw (redacted) or the
    original. Returns (faithful, total)."""
    texts = {
        r["id"]: (r["redacted"], r["orig"])
        for r in conn.execute(
            """SELECT c.id AS id, c.text_redacted AS redacted, i.text AS orig
               FROM clean_items c JOIN items i ON i.id = c.id"""
        ).fetchall()
    }
    faithful = 0
    for r in rows:
        redacted, orig = texts.get(r["item_id"], ("", ""))
        if r["quote"] in redacted or r["quote"] in orig:
            faithful += 1
    return faithful, len(rows)


def _prf(tp: int, fp: int, fn: int):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1


def main() -> int:
    conn = db.connect()
    db.init_db(conn)

    n_pred_rows = conn.execute("SELECT COUNT(*) AS c FROM pain_points").fetchone()["c"]
    if n_pred_rows == 0:
        print("No rows in `pain_points`. Run stage 2 first:")
        print("    python -m voc.orchestrator --target s2_extract")
        return 1

    gt_pairs, gt_sev, nonpain = load_ground_truth()
    pred_pairs, pred_sev, rows = load_predictions(conn)

    # --- feature-area P/R/F1 at (item, area) grain ---
    tp_set = pred_pairs & gt_pairs
    fp_set = pred_pairs - gt_pairs
    fn_set = gt_pairs - pred_pairs
    p, r, f1 = _prf(len(tp_set), len(fp_set), len(fn_set))

    # --- per-area recall (failure analysis) ---
    by_area_gt: dict[str, int] = defaultdict(int)
    by_area_tp: dict[str, int] = defaultdict(int)
    for key in gt_pairs:
        by_area_gt[key[1]] += 1
        if key in pred_pairs:
            by_area_tp[key[1]] += 1

    # --- severity accuracy on matched pairs ---
    sev_ok = sum(1 for k in tp_set if pred_sev.get(k) == gt_sev.get(k))
    sev_total = len(tp_set)

    # --- quote faithfulness ---
    faithful, q_total = quote_faithfulness(conn, rows)

    # --- non-pain precision ---
    pred_items = {k[0] for k in pred_pairs}
    nonpain_violations = sorted(nonpain & pred_items)

    dead = conn.execute("SELECT COUNT(*) AS c FROM dead_letter WHERE stage='s2_extract'").fetchone()["c"]

    # --- report ---
    print("=" * 60)
    print("STAGE 2 EVAL - pain-point extraction")
    print("=" * 60)
    print(f"predicted pain points : {n_pred_rows}")
    print(f"gt (item,area) pairs  : {len(gt_pairs)}")
    print(f"dead-lettered items   : {dead}")
    print()
    print("Feature-area match (item,area grain)")
    print(f"  precision : {p:.3f}")
    print(f"  recall    : {r:.3f}")
    print(f"  F1        : {f1:.3f}")
    print(f"  TP/FP/FN  : {len(tp_set)}/{len(fp_set)}/{len(fn_set)}")
    print()
    print("Per-area recall")
    for area in sorted(by_area_gt):
        got, tot = by_area_tp[area], by_area_gt[area]
        print(f"  {area:16s} {got:3d}/{tot:<3d}  {got/tot:.2f}")
    print()
    print(f"Severity accuracy (matched) : {sev_ok}/{sev_total}"
          f"  {sev_ok/sev_total:.3f}" if sev_total else "Severity accuracy (matched) : n/a")
    print(f"Quote faithfulness          : {faithful}/{q_total}"
          f"  {faithful/q_total:.3f}" if q_total else "Quote faithfulness          : n/a")
    print(f"Non-pain precision          : {len(nonpain) - len(nonpain_violations)}/{len(nonpain)} "
          f"clean  ({len(nonpain_violations)} false positives)")
    if nonpain_violations:
        print(f"  false-positive items: {', '.join(nonpain_violations[:10])}"
              + (" ..." if len(nonpain_violations) > 10 else ""))
    print("=" * 60)

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
