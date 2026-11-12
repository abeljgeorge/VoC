"""Build the 50-item starter golden set (stratified) from the generated data, then validate everything."""
import csv, json, random
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent
rng = random.Random(7)
t = pd.read_csv(OUT / "02_tickets/tickets.csv"); g = pd.read_csv(OUT / "02_tickets/tickets_groundtruth.csv").fillna("")
m = t.merge(g, on="id"); m = m[m.duplicate_of == ""]            # unique tickets only
rows = []

def pick(df, n, prefer_hien=0.4, exclude=()):
    df = df[~df.id.isin(exclude)]
    hi = df[df.language == "hi-en"]; other = df[df.language != "hi-en"]
    k = min(len(hi), round(n * prefer_hien))
    out = pd.concat([hi.sample(k, random_state=rng.randint(0, 999)) if k else hi.head(0),
                     other.sample(min(len(other), n - k), random_state=rng.randint(0, 999))])
    return list(out.id)

chosen = []
def add(ids): chosen.extend(i for i in ids if i not in chosen)

# special cases first
add(pick(m[m.tags.str.contains("sarcasm")], 2, 0))
add(pick(m[m.tags.str.contains("mixed_sentiment")], 2, 0))
add(pick(m[m.language == "hi"], 2, 0))
add(pick(m[m.tags.str.contains("mixed_theme")], 3, .3))
add(pick(m[m.category != "pain"], 6, .4))
quota = {"T01": 4, "T02": 4, "T03": 4, "T04": 5, "T05": 3, "T06": 3, "T07": 2, "T08": 2}
single = m[(m.category == "pain") & (~m.themes.str.contains(r"\|"))]
for th, q in quota.items():
    have = sum(th in m[m.id == c].themes.iloc[0] for c in chosen)
    need = max(0, q - have)
    if need: add(pick(single[single.themes == th], need, .6, exclude=chosen))
# top up to exactly 40 tickets, always from the theme furthest below its quota
def theme_n(th): return sum(th in m[m.id == c].themes.iloc[0].split("|") for c in chosen)
while len(chosen) < 40:
    th = min(quota, key=lambda x: theme_n(x) / quota[x])
    add(pick(single[single.themes == th], 1, .6, exclude=chosen))
chosen = chosen[:40]
for cid in chosen:
    r = m[m.id == cid].iloc[0]
    rows.append(dict(item_id=cid, source="support_ticket", language=r.language, text=r.text, themes=r.themes, severity=r.severity,
                     pain_points_json=r.pain_points_json, churn_flags=r.churn_flags, churn_evidence_json=r.churn_evidence_json,
                     tags=r.tags, category=r.category, sentiment=r.sentiment))

for iv in json.load(open(OUT / "03_interviews/interviews_groundtruth.json")):
    rows.append(dict(item_id=iv["id"], source="interview_transcript", language=iv["language"], text=iv["transcript"], themes="|".join(iv["themes"]),
                     severity=max((p["severity"] for p in iv["pain_points"]), key=["low", "medium", "high", "critical"].index),
                     pain_points_json=json.dumps(iv["pain_points"], ensure_ascii=False), churn_flags="|".join(sorted({e["flag"] for e in iv["churn_evidence"]})),
                     churn_evidence_json=json.dumps(iv["churn_evidence"], ensure_ascii=False), tags="long_form", category="pain", sentiment="mixed"))
for sc in json.load(open(OUT / "04_screenshots/screenshots_groundtruth.json"))[:6]:
    pains = sc["pain_points"]
    rows.append(dict(item_id=sc["id"], source="screenshot_chat_text", language=sc["language"], text=sc["ocr_reference"], themes="|".join(sc["themes"]),
                     severity=max((p["severity"] for p in pains), key=["low", "medium", "high", "critical"].index) if pains else "",
                     pain_points_json=json.dumps(pains, ensure_ascii=False), churn_flags="|".join(sorted({e["flag"] for e in sc["churn_evidence"]})),
                     churn_evidence_json=json.dumps(sc["churn_evidence"], ensure_ascii=False), tags="chat_ocr_reference",
                     category="pain" if pains else "non_pain", sentiment="negative" if pains else "neutral"))

gold = pd.DataFrame(rows)
gold["label_source"] = "auto_from_generation"; gold["human_verified"] = ""; gold["verifier_notes"] = ""
gold.to_csv(OUT / "05_golden/golden_set_starter.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)

# ---------------- validation ----------------
errs = []
for _, r in gold.iterrows():
    for p in json.loads(r.pain_points_json):
        if p["quote"] not in r.text: errs.append((r.item_id, "quote not verbatim", p["quote"][:40]))
    for e in json.loads(r.churn_evidence_json):
        if e["quote"] not in r.text: errs.append((r.item_id, "churn quote not verbatim"))
themes_cov = set(x for s in gold.themes for x in s.split("|") if x)
print("golden items:", len(gold), "| by source:", gold.source.value_counts().to_dict())
print("languages:", gold.language.value_counts().to_dict(), "| themes covered:", sorted(themes_cov))
print("non-pain items:", int((gold.category != "pain").sum()), "| with churn flags:", int((gold.churn_flags != "").sum()),
      "| sarcasm:", int(gold.tags.str.contains("sarcasm").sum()), "| mixed_sentiment:", int(gold.tags.str.contains("mixed_sentiment").sum()))
print("VALIDATION:", "PASS" if not errs else errs)
