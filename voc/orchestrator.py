"""Graph-shaped state machine.

Stages are nodes; their declared dependencies are edges. The runner executes
any node whose dependencies are satisfied, in topological order. This is NOT a
hard-coded line — stages 2 and 5 both depend only on stage 1, so they form the
two parallel branches from the design. Building it graph-shaped from day one
makes the later LangGraph port a mechanical node-for-node swap.

A "stage" is any module exposing this protocol:
    STAGE: str                      # unique node name, e.g. "s0_ingest"
    DEPS: list[str]                 # names of stages that must run first
    NEEDS_MODEL: str | None         # which model must be resident (I6); None = none
    def input_hash(conn) -> str     # fingerprint of this stage's input (I5)
    def run(conn) -> dict           # do the work, write rows, return stats
"""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from . import db, models
from .stages import s0_ingest, s1_clean, s2_extract


class Stage(Protocol):
    STAGE: str
    DEPS: list[str]
    NEEDS_MODEL: str | None

    def input_hash(self, conn) -> str: ...
    def run(self, conn) -> dict: ...


# Register stages here. Order does not matter — DEPS define execution order.
# Later stages (s2_extract ... s7_critic) slot in as their modules land.
REGISTRY: list[Stage] = [s0_ingest, s1_clean, s2_extract]  # type: ignore[list-item]


# --- Graph building ---------------------------------------------------------
def _topo_order(stages: list[Stage]) -> list[Stage]:
    """Kahn's algorithm. Raises on a missing dep or a cycle."""
    by_name = {s.STAGE: s for s in stages}
    for s in stages:
        for d in s.DEPS:
            if d not in by_name:
                raise ValueError(f"stage '{s.STAGE}' depends on unknown stage '{d}'")

    indeg = {s.STAGE: len(s.DEPS) for s in stages}
    ready = sorted([n for n, d in indeg.items() if d == 0])
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for s in stages:  # decrement dependents of n
            if n in s.DEPS:
                indeg[s.STAGE] -= 1
                if indeg[s.STAGE] == 0:
                    ready.append(s.STAGE)
        ready.sort()
    if len(order) != len(stages):
        raise ValueError("dependency cycle detected among stages")
    return [by_name[n] for n in order]


def _ancestors(target: str, by_name: dict[str, Stage]) -> set[str]:
    """All stages that must run before `target` (plus target itself)."""
    seen: set[str] = set()
    stack = [target]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(by_name[n].DEPS)
    return seen


# --- Runner -----------------------------------------------------------------
def run_pipeline(conn, *, target: str | None = None, run_id: str | None = None) -> None:
    """Run the graph up to and including `target` (default: everything)."""
    run_id = run_id or uuid.uuid4().hex[:12]
    by_name = {s.STAGE: s for s in REGISTRY}

    stages = REGISTRY
    if target is not None:
        if target not in by_name:
            raise ValueError(f"unknown target stage '{target}'")
        keep = _ancestors(target, by_name)
        stages = [s for s in REGISTRY if s.STAGE in keep]

    print(f"=== run {run_id} ===")
    for stage in _topo_order(stages):
        name = stage.STAGE
        ihash = stage.input_hash(conn)

        if db.cache_hit(conn, name, ihash):
            print(f"[{name}] cache hit ({ihash[:10]}) - skipped")
            db.log_run(conn, run_id=run_id, stage=name, input_hash=ihash,
                       status="skipped_cache")
            continue

        models.ensure(stage.NEEDS_MODEL)
        t0 = time.perf_counter()
        try:
            stats = stage.run(conn)
            dt = int((time.perf_counter() - t0) * 1000)
            db.log_run(conn, run_id=run_id, stage=name, input_hash=ihash,
                       status="ok", model=stage.NEEDS_MODEL, latency_ms=dt)
            summary = ", ".join(f"{k}={v}" for k, v in stats.items())
            print(f"[{name}] ok in {dt} ms - {summary}")
        except Exception as exc:  # stage-level failure: log and halt
            dt = int((time.perf_counter() - t0) * 1000)
            db.log_run(conn, run_id=run_id, stage=name, input_hash=ihash,
                       status="failed", model=stage.NEEDS_MODEL, latency_ms=dt,
                       error=f"{type(exc).__name__}: {exc}")
            print(f"[{name}] FAILED in {dt} ms - {type(exc).__name__}: {exc}")
            raise


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Run the VoC pipeline.")
    ap.add_argument("--target", help="run up to this stage only (e.g. s1_clean)")
    ap.add_argument("--db", help="override DB path")
    args = ap.parse_args(argv)

    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        run_pipeline(conn, target=args.target)
    finally:
        models.release()  # free the last resident model's memory (I6)
        conn.close()


if __name__ == "__main__":
    main()
