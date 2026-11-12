# Voice of Customer Copilot — Design Document

*Engineering design for the plan in "Voice of Customer Copilot Workflow, Tools and Portfolio Plan.md". This document is the "how it's built"; that one is the "what and why".*

---

## 1. Design goals & invariants

These are the rules the whole system is built to protect. If a design choice ever conflicts with one of these, the invariant wins.

| # | Invariant | Enforced by |
| --- | --- | --- |
| I1 | **The LLM labels, code counts.** Every number shown to a user is computed by SQL over stored rows. | Stage 4 is pure Python/SQL. The LLM is never asked "how many". |
| I2 | **Every quote is verbatim.** A quote that is not found as an exact substring of its source text is dropped, not shown. | Stage 4 substring check against `items.text`. |
| I3 | **Each agent returns validated JSON or fails loudly.** No free-text parsing downstream. | Pydantic model per agent; invalid output → retry → dead-letter. |
| I4 | **No raw customer text leaves the laptop.** Cloud stages (6, 7) receive only redacted theme summaries. | `llm.py` cloud path asserts payload contains no `items.text`. |
| I5 | **Every stage is idempotent and cached.** Re-running a stage on unchanged input produces the same output and costs nothing. | Content-hash keys in SQLite; stage skips if output for that input hash exists. |
| I6 | **One model in memory at a time.** Whisper, the LLM, and the embedder never co-reside. | Orchestrator loads/unloads per stage; 8 GB RAM / 4 GB VRAM budget. |

---

## 2. System architecture

```
                        ┌─────────────────────────────────────────────┐
   RAW SOURCES          │                 LOCAL LAPTOP                 │
   ┌──────────┐         │                                             │
   │ reviews  │─┐       │   orchestrator.py (state machine)           │
   │ tickets  │ │       │        │                                    │
   │ audio    │ ├──────▶│   ┌────▼─────┐   reads/writes   ┌─────────┐ │
   │ screens  │ │       │   │  stages  │◀────────────────▶│ SQLite  │ │
   └──────────┘─┘       │   │  0 → 7   │                  │  voc.db │ │
                        │   └────┬─────┘                  └────┬────┘ │
                        │        │ stages 6–7 only              │      │
                        └────────┼──────────────────────────────┼──────┘
                                 │ redacted theme summaries      │ export
                                 ▼                               ▼
                        ┌─────────────────┐            ┌──────────────────┐
                        │ Cloud LLM APIs  │            │ exported results │
                        │ Groq + Gemini   │            │ (SQLite or JSON) │
                        └─────────────────┘            └────────┬─────────┘
                                                                │ deploy
                                                                ▼
                                                      ┌──────────────────┐
                                                      │ Streamlit (read- │
                                                      │ only, free host) │
                                                      └──────────────────┘
```

**Two runtimes, one database.** The *pipeline* (batch, local, heavy) writes everything to `voc.db`. The *dashboard* (hosted, read-only) only reads an exported copy. They never run at the same time and share nothing but the data contract.

### Module layout

```
voc/
  orchestrator.py        # state machine: stage order, retries, model lifecycle
  db.py                  # SQLite connection, schema, run-log, cache helpers
  schemas.py             # Pydantic models = the agent contracts (section 4)
  llm.py                 # adapter: local Ollama + cloud (Groq/Gemini) + fallback
  models.py              # load/unload Whisper, LLM, embedder (one at a time)
  stages/
    s0_ingest.py
    s1_clean.py
    s2_extract.py        # LLM
    s3_cluster.py        # embeddings + BERTopic + LLM naming
    s4_evidence.py       # pure SQL — no LLM
    s5_churn.py          # regex + LLM
    s6_recommend.py      # cloud LLM
    s7_critic.py         # cloud LLM
  prompts/               # one file per LLM stage, version-controlled
  evals/                 # promptfoo configs + python scorers + golden set
  export.py              # voc.db -> exported results for the dashboard
  app/streamlit_app.py   # read-only dashboard
```

---

## 3. Data model (SQLite)

One file, `voc.db`. Each stage reads the previous table(s) and writes its own; nothing is mutated in place, so any stage can be replayed.

```sql
-- Stage 0: unified raw table
CREATE TABLE items (
  id            TEXT PRIMARY KEY,      -- stable hash of (source, source_id)
  source        TEXT NOT NULL,         -- 'playstore' | 'ticket' | 'interview' | 'screenshot'
  source_id     TEXT,                  -- original id within the source
  created_at    TEXT,                  -- ISO date
  text          TEXT NOT NULL,         -- transcript/OCR output for audio & images
  lang          TEXT,                  -- filled in stage 1
  metadata      TEXT                   -- JSON: rating, app_version, duration, etc.
);

-- Stage 1: cleaned view of items (redaction applied, dupes removed)
CREATE TABLE clean_items (
  id            TEXT PRIMARY KEY REFERENCES items(id),
  text_redacted TEXT NOT NULL,         -- PII-stripped; this is what the LLM sees
  lang          TEXT NOT NULL,
  is_duplicate  INTEGER DEFAULT 0,
  dup_of        TEXT                    -- id of the canonical item, if duplicate
);

-- Stage 2: atomic pain points (0..N per clean item)
CREATE TABLE pain_points (
  id            TEXT PRIMARY KEY,      -- hash(item_id, issue)
  item_id       TEXT NOT NULL REFERENCES items(id),
  issue         TEXT NOT NULL,         -- short normalized problem statement
  feature_area  TEXT NOT NULL,         -- 'billing' | 'food_tracking' | 'device_sync' | ...
  severity      TEXT NOT NULL,         -- 'low' | 'medium' | 'high' (matches ground truth)
  quote         TEXT NOT NULL          -- exact substring of text shown to model (verified stage 4)
);

-- Stage 3: themes and membership
CREATE TABLE themes (
  id            TEXT PRIMARY KEY,
  label         TEXT NOT NULL,         -- LLM-generated human name
  summary       TEXT                   -- 1-line, redacted; safe to send to cloud
);
CREATE TABLE theme_members (
  theme_id      TEXT NOT NULL REFERENCES themes(id),
  pain_point_id TEXT NOT NULL REFERENCES pain_points(id),
  PRIMARY KEY (theme_id, pain_point_id)
);

-- Stage 4: counts + verified quotes (computed, never model-authored)
CREATE TABLE theme_evidence (
  theme_id      TEXT PRIMARY KEY REFERENCES themes(id),
  n_mentions    INTEGER NOT NULL,      -- COUNT of distinct items in theme
  n_total       INTEGER NOT NULL,      -- denominator (items in scope)
  top_quotes    TEXT NOT NULL          -- JSON array of 2-3 verified quotes + item_id
);

-- Stage 5: churn flags (0..N per item)
CREATE TABLE churn_flags (
  item_id       TEXT NOT NULL REFERENCES items(id),
  flag          TEXT NOT NULL,         -- 'cancel' | 'refund' | 'competitor' | 'uninstall'
  method        TEXT NOT NULL,         -- 'regex' | 'llm'
  confidence    REAL,
  PRIMARY KEY (item_id, flag)
);

-- Stage 6: recommendations
CREATE TABLE recommendations (
  id            TEXT PRIMARY KEY,
  rank          INTEGER NOT NULL,
  title         TEXT NOT NULL,
  rationale     TEXT NOT NULL,
  theme_ids     TEXT NOT NULL,         -- JSON array of supporting themes
  status        TEXT NOT NULL DEFAULT 'pending'  -- set by stage 7
);

-- Stage 7: critic verdicts (history, so retries are visible)
CREATE TABLE critic_verdicts (
  rec_id        TEXT NOT NULL REFERENCES recommendations(id),
  attempt       INTEGER NOT NULL,
  verdict       TEXT NOT NULL,         -- 'approve' | 'reject'
  reason        TEXT,                  -- 'vague' | 'uncited' | 'unsupported' | null
  created_at    TEXT NOT NULL,
  PRIMARY KEY (rec_id, attempt)
);

-- Cross-cutting: observability (the "tracing" story)
CREATE TABLE run_log (
  run_id        TEXT NOT NULL,
  stage         TEXT NOT NULL,
  input_hash    TEXT NOT NULL,         -- hash of the stage's input → cache key (I5)
  status        TEXT NOT NULL,         -- 'ok' | 'retry' | 'failed' | 'skipped_cache'
  model         TEXT,                  -- which model/provider ran it
  latency_ms    INTEGER,
  tokens        INTEGER,
  error         TEXT,
  created_at    TEXT NOT NULL
);
```

**Why separate tables instead of columns on `items`:** a one-to-many (one review → many pain points) and replayability. Dropping and rebuilding `pain_points` never touches `items`.

---

## 4. Agent contracts (the heart of the system)

Each LLM stage is defined by: an input it reads, a **Pydantic output model**, a prompt, and an eval. The Pydantic model *is* the contract — the orchestrator never trusts raw model text.

### Stage 2 — Pain-point extractor (local LLM)
```python
class PainPoint(BaseModel):
    issue: str = Field(max_length=120)
    feature_area: Literal["billing","food_tracking","device_sync","onboarding",
                          "login_stability","coaching","personalization","other"]
    severity: Literal["low","medium","high"]
    quote: str                       # must be verbatim; checked later

class ExtractionResult(BaseModel):
    pain_points: list[PainPoint]     # may be empty (not every review has one)
```
Prompt rule: *"Quote must be copied character-for-character from the review. If no concrete pain point, return an empty list."* Uses Ollama structured output (JSON schema) so malformed JSON is measured, not silently retried.

### Stage 3 — Theme namer (local LLM)
Clustering itself is BERTopic (not the LLM). The LLM only **names** a cluster from its representative members.
```python
class ThemeName(BaseModel):
    label: str = Field(max_length=60)
    summary: str = Field(max_length=200)   # redacted, cloud-safe
```

### Stage 5 — Churn classifier (local LLM, second pass)
Regex catches the obvious cases first and writes `method='regex'`. The LLM only sees items the regex did **not** flag, to catch subtle intent.
```python
class ChurnJudgment(BaseModel):
    flags: list[Literal["cancel","refund","competitor","uninstall"]]
    confidence: confloat(ge=0, le=1)
```

### Stage 6 — Roadmap recommender (cloud LLM, Groq)
Input: a JSON summary of themes with counts and churn flags — **no raw text** (I4).
```python
class Recommendation(BaseModel):
    title: str
    rationale: str
    theme_ids: list[str]             # must reference real themes (validated)

class RoadmapResult(BaseModel):
    recommendations: list[Recommendation]   # ranked by list order
```
Post-validation: every `theme_id` must exist in `themes`. A recommendation citing a non-existent theme is rejected before it reaches the critic.

### Stage 7 — Critic / verifier (cloud LLM, Gemini — different family on purpose)
```python
class Verdict(BaseModel):
    verdict: Literal["approve","reject"]
    reason: Optional[Literal["vague","uncited","unsupported"]] = None
```
Rule: `reject` requires a `reason`; `approve` forbids one. Enforced by a Pydantic validator.

---

## 5. The LLM adapter (`llm.py`)

One function, three backends, uniform behaviour. This is what makes the cloud/local story honest and the project survive a rate-limit change.

```python
def complete(prompt: str, schema: type[BaseModel], *, route: str) -> BaseModel:
    # route in {"local", "recommender", "critic"}
    # 1. pick provider: local→Ollama, recommender→Groq, critic→Gemini
    # 2. for cloud routes: assert no raw item text in prompt  (I4)
    # 3. call with JSON-schema / structured-output mode
    # 4. parse into `schema`; on ValidationError → retry once with the error echoed
    # 5. on repeated failure or rate-limit → fall back to local Ollama
    # 6. log provider, latency, tokens, status to run_log
```

Key properties:
- **Fallback is automatic.** If Groq/Gemini is down or throttled, the stage runs on Ollama. The project never hard-fails on a free-tier limit.
- **Redaction assertion is a hard gate**, not a lint. A cloud call carrying raw text raises before the request is sent.
- **Validation-aware retry:** the retry prompt includes the Pydantic error, which materially lifts valid-JSON rate on small models.

---

## 6. Orchestration & execution flow

### 6.1 Control flow

The orchestrator is a **graph-shaped state machine from day one**: stages are nodes, dependencies are edges, and the runner executes any node whose inputs are ready. It is *not* a hard-coded line — stages 2 and 5 both depend only on `clean_items`, so they form the two parallel branches; both must finish before stage 6. We hand-roll this graph first (a dict of `node -> {deps, fn}` plus a topological runner), which keeps full control over caching, model lifecycle and logging. The LangGraph port is then a mechanical node-for-node swap, giving an honest before/after comparison without restructuring any stage logic. Building graph-shaped from the start is what makes that port cheap.

```
        ┌──────────────── dependency graph ────────────────┐
        0  ─▶  1  ─┬─▶  2  ─▶  3  ─▶  4  ─┐
                   │                      ├─▶  6  ⇄  7  ─▶ (export → dashboard)
                   └─▶  5  ───────────────┘       │
                                          reject loop ≤2, then → human_review
```

### 6.2 Per-stage execution contract

Every stage, when the orchestrator calls it, does exactly this:

1. **Compute `input_hash`** over its input rows + prompt version + model id.
2. **Cache check (I5):** if `run_log` has `status='ok'` for `(stage, input_hash)`, skip and return the stored output. This is what lets you crash on stage 5 and resume without re-running stages 0–4.
3. **Ensure the right model is resident (I6):** ask `models.py` to load what this stage needs and unload anything else. (Stage 4 loads nothing.)
4. **Run the work**, producing validated rows.
5. **Write output table + a `run_log` row** (status, model, latency, tokens).
6. On exception: log `status='failed'`, write the offending input to a dead-letter table, and either continue (per-item failure) or halt (stage-level failure) per policy.

### 6.3 Failure & retry policy

| Failure | Granularity | Policy |
| --- | --- | --- |
| One review fails Pydantic in stage 2 | per-item | retry once (error-echo prompt) → dead-letter that item → continue the batch |
| Quote not verbatim (stage 4 check) | per-quote | drop the quote; if a theme has <1 valid quote, flag it low-evidence, don't invent |
| Cloud rate-limit / outage (stage 6/7) | per-call | `llm.py` falls back to local Ollama; log the downgrade |
| Critic rejects a recommendation (stage 7) | per-rec | loop back to stage 6 with the reason, max 2 attempts, then → `human_review` queue |
| Whole stage throws | per-stage | halt pipeline; the cache means re-run resumes at the failed stage |

### 6.4 Resource lifecycle (the 8 GB reality)

```
stage 0 ─ load Whisper → transcribe → UNLOAD
stage 1 ─ (no model) pandas + langdetect + Presidio
stage 2 ─ load LLM → extract → keep resident (stage 3 naming reuses it)
stage 3 ─ load embedder → BERTopic → UNLOAD embedder; LLM names themes → UNLOAD LLM
stage 4 ─ (no model) pure SQL
stage 5 ─ load LLM → classify residual items → UNLOAD
stage 6 ─ cloud call (no local model)
stage 7 ─ cloud call (no local model)
```
Caching to SQLite after each stage means a model is loaded, used for the whole batch, and unloaded exactly once. Batch big jobs overnight.

---

## 7. Dashboard ↔ pipeline boundary

`export.py` reads `voc.db` and writes a **read-only** artifact (a trimmed SQLite file or JSON bundle) containing only: themes, evidence (counts + verified quotes), churn aggregates, recommendations + verdicts. No raw `items.text`. The Streamlit app loads that artifact and renders — it never imports `voc` pipeline code and never calls an LLM. This is why it can live on a free host that can't run Ollama: all the thinking already happened locally.

---

## 8. Observability

`run_log` is the single source of truth for "what happened". It answers, with SQL:
- Which stage failed and why (`status='failed'`, `error`).
- Which stages were cache hits vs recomputed.
- Per-stage latency, token spend, and which provider/model served each call (including cloud→local fallbacks).
- Reconstruct any recommendation's full critic history from `critic_verdicts`.

This is the cheap version of tracing; Arize Phoenix is an optional add-on, not a dependency.

---

## 9. Open design questions (carried from the plan)

- **Hinglish share** sets how hard the multilingual requirement is — measure it on the first scrape before freezing the bake-off weighting.
- **Cluster granularity:** BERTopic's HDBSCAN min-cluster-size needs tuning on real data; too large merges distinct pains, too small fragments them.
- **Critic calibration:** the critic is only trustworthy if its verdicts track your hand labels — calibrate on a sample before relying on the reject loop.
- **Embedding upgrade trigger:** stay on multilingual-e5-small unless cluster coherence scores are weak, then try bge-m3.
