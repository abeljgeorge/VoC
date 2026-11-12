# Voice of Customer Copilot

Multi-agent workflow, free-tool stack and portfolio plan

*AI PM portfolio project · October 2026 · Draft v2*

## 1. Overview

**Problem:** Product teams receive customer feedback from many messy sources (Play Store reviews, support tickets, sales calls, interviews, WhatsApp screenshots) and struggle to turn it into roadmap decisions.

**Solution:** A pipeline of specialist AI agents that finds pain points, clusters them into themes, attaches real quotes, flags churn signals and recommends what to build next.

**Domain:** Wellness, fitness and sport apps, starting with HealthifyMe (Google Play reviews). Likely pain points are subscription billing, tracking accuracy, device sync and onboarding (to be confirmed by the data). Cancellation and refund language gives the churn detector clear signals to find.

**Design principles**

- **The LLM labels, code counts.** Numbers like "12 of 50 reviews" come from SQL, never from the model, so they can't be hallucinated.
- **Specialist agents with strict contracts.** Each agent does one job and returns validated JSON. Each gets its own eval.
- **Local-first, near-zero budget.** Ollama runs the per-review work on your laptop. A free-tier cloud LLM handles only the last two stages and sees redacted theme summaries, never raw reviews.

**Output quality bar (from your notes)**

|  | Example |
| --- | --- |
| Bad | "Users are unhappy with onboarding." |
| Good | "12 of 50 reviews mention onboarding confusion. 5 users said they could not complete the first setup step." (with quotes) |

## 2. Workflow

The orchestrator runs eight stages in order. Each stage reads the previous stage's output from the database and writes its own.

&#91;embedded content: pipeline · 8 stages, 2 parallel branches, 1 retry loop\]

Cleaned rows feed two branches in parallel. Both merge into the recommender, and the critic sends rejected output back before it reaches the dashboard.

| # | Stage | Input | Output | Runs on |
| --- | --- | --- | --- | --- |
| 0 | Ingestion | Reviews, tickets, audio, screenshots | One unified table: id, source, date, text, metadata | Local (Whisper, OCR) |
| 1 | Cleaning and enrichment | Raw rows | Deduplicated, language-tagged, PII-redacted rows | Local |
| 2 | Pain-point extractor | Clean rows | Atomic pain points: issue, feature area, severity, exact quote | Local LLM |
| 3 | Clustering | Pain points | Named themes with member lists | Local embeddings and LLM |
| 4 | Evidence and counts | Themes | "X of Y" counts plus 2–3 verified quotes per theme | Local code (SQL) |
| 5 | Churn-signal detector | Clean rows | Flags: cancel intent, refund or billing dispute, competitor mention, uninstall | Local rules and LLM |
| 6 | Roadmap recommender | Themes, counts, churn flags | Ranked roadmap items with rationale | Free-tier cloud LLM |
| 7 | Critic/verifier | Recommendations | Approve, or reject with reason (vague, uncited, unsupported) | Free-tier cloud LLM |

A rejected output loops back to stage 6 once or twice, then goes to a human review queue.

## 3. Tool evaluation (free and local)

**Selection criteria:** cost (free), runs on a laptop, good enough quality for the task, and easy to explain in an interview.

| Stage | Pick | Alternatives considered | Why this pick |
| --- | --- | --- | --- |
| Models (local) | **Ollama** with the winner of a model bake-off (Phi-4-mini, Gemma 3 4B, Qwen3 4B) at 4-bit | 7–9B models, cloud APIs | Fits your 4 GB GPU. A 7–9B model spills into CPU on 8 GB RAM and runs very slowly. Check the Ollama library for the current best small model |
| Models (cloud, stages 6–7 only) | **Free-tier hosted LLM API** from Groq (recommender) and Gemini (critic) | OpenRouter free models, paid APIs | Recommending and criticizing need stronger reasoning than a 3–4B model gives. Input is a small, redacted theme summary, so free limits are enough. Different model families stop the critic grading its own work. Wrap both in one llm.py adapter with Ollama as the fallback, and check current limits in each console |
| Play Store data | **google-play-scraper** (Python) | Manual Play Console CSV | Free and quick for one app. Use for development, but ship only a small, redacted sample |
| Tickets | **Synthetic tickets** written and edited by you | Real company data | Script billing, cancellation and sync complaints. No privacy risk and fully reproducible |
| Calls and interviews | **3–5 short mock interviews** you record from LLM-drafted scripts built around planted themes | Real calls, public transcripts | Realistic, no consent issues, and the planted themes give you ground truth, plus audio to measure transcription errors |
| Audio to text | **faster-whisper** (base or small, int8) | openai-whisper, cloud ASR | Free and runs on CPU or the 4 GB GPU. Run it as its own step, never alongside the LLM. Optional upgrade: Groq's free-tier Whisper for better Hinglish accuracy, with this as the local fallback |
| Screenshots | **Tesseract OCR**, then the local LLM structures the messages (EasyOCR if accuracy is poor). Test set: about 10 HTML/CSS chat renders (Playwright) plus about 5 real screenshots of a scripted WhatsApp chat | Local vision model, cloud vision | A vision model will not fit comfortably in 8 GB RAM. OCR is light and good enough for clean chat screenshots |
| Cleaning | **pandas, langdetect, Microsoft Presidio** | Hand-written regex | Presidio is the standard open-source PII tool |
| Embeddings | **multilingual-e5-small** (sentence-transformers, CPU) | bge-m3, nomic-embed-text | Small multilingual model that handles Hinglish and leaves RAM free. Upgrade to bge-m3 only if clusters look weak |
| Clustering | **BERTopic (UMAP + HDBSCAN)** | KMeans, LLM-only grouping | Finds the number of clusters itself and is a recognizable method. Name themes with the local LLM |
| Storage | **SQLite** (+ sqlite-vec or Chroma if needed) | Postgres + pgvector | Zero setup, a single file, and easy to ship. Move to Postgres only if you outgrow it |
| Churn detection | **Regex rules + local LLM classifier** | LLM only | Rules are cheap and precise for obvious cases (cancel, refund, auto-renewal). The LLM catches subtle ones |
| Validation | **Pydantic** | Manual checks | Enforces every agent's JSON contract |
| Orchestration | **Plain Python state machine** first, then port to **LangGraph** | CrewAI, AutoGen | Debug the simple version first, then port it and compare. You get a recognizable CV keyword and an honest before and after |
| Dashboard | **Streamlit** | Gradio, Next.js | Fastest path and a free host (see section 4) |
| Evals | **Promptfoo** (supports Ollama) plus your own Python scripts | Ragas, DeepEval | Promptfoo is free and simple for prompt comparisons |
| Tracing | **SQLite run-log table** (Arize Phoenix optional) | Langfuse self-hosted | Langfuse needs Docker, which competes for your 8 GB RAM. Add Phoenix only if time allows |

### Model sizing for 8 GB RAM and a 4 GB GPU

- **Your machine (i5-9300H, 8 GB RAM, GTX 1650 4 GB):** a 3–4B model at 4-bit fits on the GPU. A 7–9B model does not, and will crawl on CPU.
- **Run stages one at a time.** Load Whisper, the LLM and the embedder separately, and unload each before the next. Cache every stage's output in SQLite so you never rerun it.
- **Free up memory.** Close other apps and keep Docker off, because Windows alone takes a large share of 8 GB.
- **Keep v1 data small:** one app, a few hundred to a thousand reviews, and a handful of audio clips and screenshots. Batch jobs can run overnight.
- **One small model for stages 2, 3 (labels) and 5.** Stages 6 and 7 use the free-tier cloud LLM.

### Model bake-off

**Goal:** pick the best local model for each stage using your own data instead of leaderboards. Do it in week 2, once a 50-item starter golden set exists.

| Candidate | Ollama tag (check the library for current tags) | Why test it | Watch for |
| --- | --- | --- | --- |
| Phi-4-mini (3.8B) | phi4-mini | Strong reasoning and instruction following for its size, and about 3 GB at 4-bit, so it fits your GPU | Hindi and Hinglish quality is unknown, so test it |
| Gemma 3 4B | gemma3:4b | Good all-round quality and wide language coverage | About 4.2 GB, so it may spill to CPU on 4 GB of VRAM and run slower |
| Qwen3 4B | qwen3:4b | Strong multilingual coverage and structured output | Thinking mode adds latency, so turn it off for extraction |

**Method**

1. Freeze everything except the model: one prompt and one JSON schema per stage, temperature 0, identical inputs.
2. Run each candidate on stages 2, 3 (theme labels) and 5 through Promptfoo's Ollama provider, using the starter golden set.
3. Use Ollama's structured output (JSON schema), so format failures are measured and not hidden.
4. Unload the model between runs so each gets the full 4 GB and a fair speed reading.
5. Fill in the scorecard below for every candidate.

| Metric | How to measure | Why it matters |
| --- | --- | --- |
| Valid JSON rate | Share of outputs that pass Pydantic on the first try | Retries cost time |
| Pain-point recall and precision | Against your labels | The core quality measure |
| Quote faithfulness | Share of quotes found verbatim in the source | Code enforces 100% later, but the raw rate shows how often the model invents text |
| Hinglish accuracy | Recall on your Hinglish items only | The biggest domain risk |
| Speed | Reviews per minute at your context size | Decides whether a full run fits overnight |
| Peak memory | VRAM and RAM in use | Your 8 GB RAM leaves little headroom |

**Decision rule:** per stage, pick the model with the best recall among those with at least 95% valid JSON on the first try, and break ties on speed. A different winner per stage is fine. If every candidate misses your recall target, try a 7–8B model on a free Kaggle or Colab GPU for the bulk stage, or move stage 2 to the cloud API. Keep the full scorecard for your eval report.

### Where free tools will limit you

- **Hinglish and mixed-language reviews:** small models make more mistakes. Test early and report the error rate honestly.
- **A 3–4B model misses subtle pain points.** Constrain it with JSON schemas and short prompts, and measure it against your golden set.
- **Free cloud limits can change.** Keep a local fallback for stages 6 and 7 so the project still runs if a limit tightens.
- **LLM-as-judge is only as good as its calibration.** Rely on your hand labels and code checks, and calibrate any judge against your own ratings.
- **Free hosts can't run Ollama.** Solve this with precomputed results (next section).

## 4. Architecture and hosting

**Run locally:** raw data → pipeline (Python + Ollama, with stages 6 and 7 calling a free-tier cloud LLM) → SQLite → Streamlit dashboard.

**Publish for free:** run the pipeline on your machine, export the results (themes, counts, quotes, recommendations) to SQLite or JSON, and deploy a read-only Streamlit app to Streamlit Community Cloud or Hugging Face Spaces. Recruiters get a live link, and your README explains how to run the full pipeline locally.

&#91;embedded content: architecture · local pipeline, free read-only host\]

Ollama never leaves your machine, and the cloud LLM sees only redacted theme summaries. The hosted app only reads the exported results.

## 5. Dashboard (from your sketch)

&#91;embedded content: dashboard wireframe · sidebar, 4 cards, 3 charts, 1 quote panel\]

Shapes show layout only; the real charts are drawn from pipeline output.

| Area | Content |
| --- | --- |
| Left sidebar (Reviews) | Source and date filters, raw feed |
| Top cards (4) | Feedback analyzed, top theme, churn-risk count, new themes this week |
| Bar chart | Pain points ranked by frequency |
| Line chart | Theme trend over time (shows whether a release fixed an issue) |
| Bubble cluster | Themes sized by volume, colored by severity |
| Bottom-right panel | Verified quotes and churn alerts for the selected theme |
| AI Recommendations tab | Ranked roadmap items, each with evidence and the critic's verdict |

## 6. Evals

Hand-label a golden set of 100–150 items yourself. Start with 50 for the model bake-off in week 2, then grow it.

| Component | Metric | Target |
| --- | --- | --- |
| Pain-point extraction | Precision and recall vs your labels | Report both, iterate prompts |
| Clustering | Human-rated coherence on about 20 clusters | Report % coherent |
| Quote faithfulness | Quote exists verbatim in the source text (transcript or OCR output for audio and screenshots) | 100% (enforced by code) |
| Counts | Match to SQL | 100% (computed by code) |
| Churn flags | Precision and recall | Report both |
| Recommendations | 1–5 rubric: specificity, evidence, actionability | Average score, before vs after iteration |
| Audio transcription | Word error rate on hand-checked mock interview clips | Report it, and note where accents or Hinglish fail |
| Screenshot extraction | Share of messages OCR reads correctly | Report it, with failure examples |

Include a **failure analysis** (where it breaks and why). Reviewers value this more than a perfect score.

## 7. Build plan

| Week | Goal |
| --- | --- |
| 1 | Collect a small HealthifyMe review sample, write synthetic tickets, record mock interviews, make mock screenshots. Set up Ollama and SQLite. Build stages 0–1, including Whisper and OCR |
| 2 | Label a 50-item starter golden set, run the model bake-off, then build stages 2–4 (extract, cluster, evidence and counts) and a basic Streamlit view |
| 3 | Churn detector, recommender and critic (free-tier cloud LLM), full dashboard |
| 4 | Extend the golden set to 100–150 items, run final evals, write the failure analysis, README and demo video, deploy |
| 5 | Port the orchestrator from plain Python to LangGraph and compare results |

## 8. Portfolio packaging

| Asset | What it contains |
| --- | --- |
| One-page problem framing | Who the user is, the pain, why current tools fall short, success metrics |
| Workflow diagram | The pipeline and agent contracts (section 2) |
| Case study write-up | Decisions and trade-offs: why local models with a cloud step for the last two stages, why code-computed counts, why a critic, plain Python vs LangGraph |
| Eval report | Metrics, model bake-off results, prompt iterations (before and after), failure analysis |
| Live demo | Read-only Streamlit app with a public link |
| 2-minute demo video | Problem, one insight found, the recommendation, the evidence behind it |
| GitHub repo | Clean README, setup steps, sample data, architecture diagram, license |
| Ethics note | Public or synthetic data only (mock interviews and screenshots are scripted by you), PII redacted, no raw scraped dump published |

**Order of work:** build, then evals, then write-up, then video. Write the case study while you still remember the trade-offs.

## 9. Decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Domain | Wellness, fitness and sport apps | Plentiful public reviews and clear churn signals (billing, cancellation, refunds) |
| App | HealthifyMe (Google Play reviews). Fallbacks: cult.fit, Strava | Indian app with Hinglish reviews and billing complaints. Strava is the easy-volume fallback, cult.fit the churn-signal fallback |
| Orchestration | Plain Python first, LangGraph in week 5 | Easy to debug first, and gives you a before and after comparison |
| Local models | Ollama, with a bake-off between Phi-4-mini, Gemma 3 4B and Qwen3 4B | Choose on your own golden set, not leaderboards |
| Cloud models | Groq (recommender) and Gemini API (critic), free tiers, behind one adapter with Ollama as fallback | Different model families avoid the critic grading its own work. Check current limits in each console |
| Audio | LLM-drafted scripts with planted themes, recorded by you. faster-whisper, with Groq Whisper optional | Planted themes give ground truth, and real voices test accents and Hinglish |
| Screenshots | About 10 HTML/CSS chat renders plus about 5 real scripted WhatsApp screenshots, read with Tesseract | Renders give exact ground truth, and real ones test messy layouts |

**Next checks**

- Confirm current free-tier limits in the Groq console and Google AI Studio
- Scrape a small HealthifyMe sample (google-play-scraper is unofficial) and measure the Hinglish share, which sets how much multilingual quality matters in the bake-off
- Write the theme list that your mock scripts and screenshots will plant
