# VoC Copilot: synthetic data pack (v1)

Fictional wellness/fitness app for Indian users (HealthifyMe-style). The app name never appears in the data. Everything here is generated from one theme list, so every label in the answer keys is exact by construction.

## Folder map
| Path | What it is | Use it for |
|---|---|---|
| `01_themes/themes.json` | 8 planted themes, 36 issues, churn flags, release/pricing events | Source of truth; theme naming for stage 3 |
| `01_themes/planted_counts.json` | True counts per theme, issue, language, churn flag | Checking stage 4 "X of Y" counts |
| `01_themes/planted_trend_by_week.csv` | True weekly theme counts | Checking the trend chart |
| `02_tickets/tickets.csv` | **Pipeline input.** 186 tickets: id, source, date, text, metadata | Stage 0 input |
| `02_tickets/tickets_groundtruth.csv` | **Answer key (do not feed to the pipeline).** Pain points with exact quotes, themes, churn flags, PII, duplicates | Evals for stages 1-5 |
| `02_tickets/events.csv` | Release 8.4.0 (18 Aug), hotfix 8.4.1 (15 Sep), price change (20 Sep) | Root-cause linking |
| `03_interviews/scripts/*.md` | 4 mock interview scripts (2 Hinglish) to record yourself | Whisper test |
| `03_interviews/interviews_groundtruth.json` | Transcripts, pain points, churn evidence | WER reference and extraction eval |
| `04_screenshots/renders/` | 10 WhatsApp-style chats as HTML + PNG (light/dark, 3 widths) | OCR test with exact ground truth |
| `04_screenshots/real_whatsapp_scripts.md` | 5 scripts for you to enact on real WhatsApp | Messy real-layout OCR test |
| `04_screenshots/*_groundtruth.json` | Message text, pain points, churn evidence per image | OCR and extraction evals |
| `05_golden/golden_set_starter.csv` | 50 items (40 tickets, 4 interviews, 6 chats) with pre-filled labels | Week-2 model bake-off |
| `scripts/` | Reproducible generators (`python generate_tickets.py`, seed 42) | Regenerate or scale up |

## Planted themes (unique tickets, duplicates excluded)
| ID | Theme | Area | Tickets | Volume pattern |
|---|---|---|---|---|
| T01 | Unexpected subscription charges | billing | 30 | high |
| T02 | Cancellation and refund friction | billing | 25 | high |
| T03 | Food logging and calorie inaccuracy | food_tracking | 26 | high |
| T04 | Wearable and step sync failures | device_sync | 33 | high (spike) |
| T05 | Onboarding and setup confusion | onboarding | 20 | medium |
| T06 | Login, OTP and app stability | login_stability | 16 | medium (spike) |
| T07 | Coach responsiveness and value for price | coaching | 11 | low |
| T08 | Diet plan does not fit my needs | personalization | 7 | rare |

Churn flags planted: cancel_intent 28, refund_dispute 32, uninstall 14, competitor_mention 10.

## Built-in test cases
- **Languages:** 114 English, 61 Hinglish (Roman script), 5 Hindi (Devanagari).
- **Stage 1 (cleaning):** 6 duplicates (3 exact, 3 near, listed in `duplicate_of`), 37 tickets with fake PII (names, phones, emails; exact values in `pii_json`), 40 noisy texts (ALL CAPS, typos, no punctuation, `!!!`).
- **Stage 2 (extraction):** 4 sarcastic tickets (5 rows, one is duplicated), 6 mixed-sentiment, 8 two-theme tickets, 20 non-pain tickets (praise, questions, feature requests) to test precision.
- **Stage 3-4:** a rare theme (T08) to test long-tail detection; a clean spike (T04, T06) and a step change (T01, T02) for the trend chart.
- **Quotes:** every `quote` in every answer key is a verbatim substring of its source text (asserted in code).

## Caveats
- **Hinglish is LLM-written.** Spelling is consistent, real users vary a lot. Review it and add your own variants before trusting Hinglish scores.
- The golden set is **auto-labeled from generation**. The plan says to hand-label: use `human_verified` and `verifier_notes` to record your check of each row, and fix anything you disagree with.
- Phone numbers and emails are random fakes (emails use example.com). No emojis in v1 (render fonts).
- The real HealthifyMe reviews (scraped) are not included. Add ~10 hand-labeled review items to the golden set once you have them, because synthetic text is tidier than real reviews.
- OCR sanity check on the renders: Tesseract mean similarity 0.92 (`scripts/ocr_baseline.py`).

## Your remaining manual steps
1. Record the 4 interview scripts (1-2 min each).
2. Enact and screenshot the 5 real WhatsApp scripts.
3. Verify the golden set rows, then add real review items.
