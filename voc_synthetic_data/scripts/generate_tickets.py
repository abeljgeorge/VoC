"""Generate synthetic support tickets + answer key. Reproducible: python generate_tickets.py"""
import csv, json, random, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from content import *

OUT = Path(__file__).resolve().parent.parent
rng = random.Random(42)

D = dt.date
START, END = D(2026, 7, 1), D(2026, 10, 31)
REL, FIX, PRICE = D(2026, 8, 18), D(2026, 9, 15), D(2026, 9, 20)
AREA = {t: v["feature_area"] for t, v in THEMES.items()}

SINGLE_COUNTS = {"T01": 28, "T02": 22, "T03": 24, "T04": 30, "T05": 18, "T06": 14, "T07": 10, "T08": 6}
MIXED_PAIRS = [("T01", "T02"), ("T01", "T02"), ("T04", "T06"), ("T04", "T06"), ("T03", "T05"), ("T07", "T02"), ("T05", "T08"), ("T03", "T04")]
NONPAIN_N = 20
FORCE_HI = ["T01", "T02", "T03", "T04", "T05"]      # first ticket of these themes is Devanagari Hindi
FORCE_SAR = ["T01", "T02", "T04", "T05"]            # second ticket of these themes is sarcastic
N_MIXED_SENTIMENT, N_DUP_EXACT, N_DUP_NEAR = 6, 3, 3


# ---------- helpers ----------
def rand_date(a, b):
    return a + dt.timedelta(days=rng.randint(0, (b - a).days))

def windows_for(theme):
    """(start, end, weight) windows that plant the trends."""
    if theme == "T04":
        return [(START, REL - dt.timedelta(1), .2), (REL, FIX - dt.timedelta(1), .6), (FIX, END, .2)]
    if theme == "T06":
        return [(REL, REL + dt.timedelta(10), .55), (START, END, .45)]
    if theme in ("T01", "T02"):
        return [(START, PRICE - dt.timedelta(1), .35), (PRICE, END, .65)]
    return [(START, END, 1.0)]

def allocate_dates(theme, n):
    """Evenly spread (with jitter) inside each window so planted trends are clean, not clumpy."""
    wins, out = windows_for(theme), []
    for a, b, w in wins:
        m, span = round(n * w), (b - a).days + 1
        out += [a + dt.timedelta(days=min(span - 1, int((i + rng.random()) / m * span))) for i in range(m)]
    while len(out) < n: out.append(rand_date(*wins[0][:2]))
    out = out[:n]; rng.shuffle(out); return out

def with_time(d):
    return dt.datetime(d.year, d.month, d.day, rng.randint(8, 22), rng.randint(0, 59))

def slots():
    food, c1, c2 = rng.choice(FOODS); amt = rng.choice([1499, 2499, 2999, 3999])
    return dict(amt=f"{amt:,}", amtlow=f"{amt - 500:,}", day=rng.choice([5, 6]), d=rng.randint(7, 21), dn=rng.randint(2, 4),
                plan=rng.choice(PLANS), device=rng.choice(DEVICES), steps=f"{rng.randint(60, 120) * 100:,}",
                food=food, c1=c1, c2=c2, home=rng.choice(HOME_DISHES), comp=rng.choice(COMPETITORS),
                kg=rng.randint(3, 12), m=rng.randint(2, 6))

def noise(s, tags):
    if rng.random() > .2: return s
    kind = rng.choice(["lower", "caps", "typo", "exclaim"])
    if kind == "lower": s = s.lower().rstrip(".")
    elif kind == "caps": s = s.upper()
    elif kind == "exclaim": s = s.rstrip(".") + "!!!"
    else:
        words = s.split(); cand = [i for i, w in enumerate(words) if len(w) >= 5 and w.isalpha()]
        if cand:
            i = rng.choice(cand); w = list(words[i]); j = rng.randint(0, len(w) - 2); w[j], w[j + 1] = w[j + 1], w[j]
            words[i] = "".join(w); s = " ".join(words)
    tags.add("noisy"); return s

def fake_pii(lang):
    first, last = rng.choice(FIRST), rng.choice(LAST)
    phone = f"+91 {rng.choice('6789')}{rng.randint(1000, 9999)} {rng.randint(10000, 99999)}"
    email = f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.com"
    return first, last, phone, email

def pii_block(lang, tags):
    """Return (inline_sentence, signature, pii_list) or empty."""
    if rng.random() > .28: return "", "", []
    first, last, phone, email = fake_pii(lang)
    name = f"{first} {last}"; kind = rng.choice(["name", "name_phone", "email", "phone"])
    inline = sig = ""; pii = []
    if kind in ("name", "name_phone"):
        sig = rng.choice(["Regards,\n", "Thanks,\n", "- "]) + name; pii.append(("PERSON", name))
    if kind in ("name_phone", "phone"):
        inline = (f"My registered mobile number is {phone}." if lang != "hi-en" else f"Mera registered number {phone} hai.")
        pii.append(("PHONE_NUMBER", phone))
    if kind == "email":
        inline = f"My email is {email}." if lang != "hi-en" else f"Mera email {email} hai."; pii.append(("EMAIL_ADDRESS", email))
    tags.add("pii"); return inline, sig, pii

def pick_fragment(theme, lang, k):
    pool = [f for f in FRAGMENTS if ISSUES[f["issue"]][0] == theme]
    if k == 0 and theme in FORCE_HI:
        return rng.choice([f for f in pool if f["lang"] == "hi"])
    if k == 1 and theme in FORCE_SAR:
        return rng.choice([f for f in pool if f["sar"]])
    pool = [f for f in pool if f["lang"] == lang and not f["sar"]] or [f for f in pool if f["lang"] == "en" and not f["sar"]]
    return rng.choice(pool)

def build(frag_specs, when, kind="pain", mixed_sentiment=False):
    lang = frag_specs[0]["lang"]; tags, pains, flags, evidence, parts = set(), [], set(), [], []
    s = slots()
    for j, spec in enumerate(frag_specs):
        raw = spec["x"].format_map(s)
        if lang != "hi": raw = noise(raw, tags)
        theme, label, sev = ISSUES[spec["issue"]]
        pains.append(dict(issue_id=spec["issue"], issue=label, theme_id=theme, feature_area=AREA[theme], severity=sev, quote=raw))
        for fl in spec["flags"]: flags.add(fl); evidence.append(dict(flag=fl, quote=raw))
        if spec["sar"]: tags.add("sarcasm")
        parts.append((JOIN[lang] if j else "") + raw)
    if len(frag_specs) > 1: tags.add("mixed_theme")
    body = "".join(parts)
    if mixed_sentiment and lang in PRAISE_PREFIX:
        body = rng.choice(PRAISE_PREFIX[lang]) + body; tags.add("mixed_sentiment")
    if lang in DETAILS and DETAILS[lang] and rng.random() < .35: body += " " + rng.choice(DETAILS[lang])
    # churn add-ons
    billing = any(p["theme_id"] in ("T01", "T02") for p in pains)
    if rng.random() < (.35 if billing else .12):
        fl = rng.choice(["cancel_intent", "refund_dispute", "uninstall", "competitor_mention"] if billing else ["cancel_intent", "uninstall", "competitor_mention"])
        opts = ADDONS[fl].get(lang) or ADDONS[fl]["en"] if lang != "hi" else ADDONS[fl]["hi"]
        if opts:
            txt = rng.choice(opts).format_map(s); body += " " + txt; flags.add(fl); evidence.append(dict(flag=fl, quote=txt))
    inline, sig, pii = pii_block(lang, tags)
    if inline: body += " " + inline
    text = (rng.choice(OPENERS[lang]) + "\n\n" if rng.random() < .5 else "")
    text = (rng.choice([o for o in OPENERS[lang] if o]) + "\n\n" if rng.random() < .5 else "") + body
    c = rng.choice([c for c in CLOSERS[lang]]); text += (" " + c if c else "")
    if sig: text += "\n\n" + sig
    themes = []
    for p in pains:
        if p["theme_id"] not in themes: themes.append(p["theme_id"])
    sev_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    sev = max((p["severity"] for p in pains), key=lambda x: sev_rank[x])
    return dict(text=text.strip(), lang=lang, when=when, category="pain", themes=themes, pains=pains, flags=sorted(flags),
                evidence=evidence, tags=tags, pii=pii, severity=sev, sentiment="mixed" if "mixed_sentiment" in tags else "negative", dup_of=None)

# ---------- build base tickets ----------
tickets = []
mixed_sentiment_budget = N_MIXED_SENTIMENT
for theme, n in SINGLE_COUNTS.items():
    dates = allocate_dates(theme, n)
    for k in range(n):
        lang = "en" if rng.random() < .64 else "hi-en"
        spec = pick_fragment(theme, lang, k)
        ms = spec["lang"] != "hi" and not spec["sar"] and mixed_sentiment_budget > 0 and rng.random() < .1 and spec["lang"] in PRAISE_PREFIX
        if ms: mixed_sentiment_budget -= 1
        tickets.append(build([spec], with_time(dates[k]), mixed_sentiment=ms))
for a, b in MIXED_PAIRS:
    lang = "en" if rng.random() < .75 else "hi-en"
    specs = [pick_fragment(t, lang, 9) for t in (a, b)]
    for sp in specs: sp["lang"] = sp["lang"]
    w = rng.choices(windows_for(a), weights=[x[2] for x in windows_for(a)])[0]
    tickets.append(build(specs, with_time(rand_date(w[0], w[1]))))
for i in range(NONPAIN_N):
    cat, lang, txt = NONPAIN[i % len(NONPAIN)] if i < len(NONPAIN) else rng.choice(NONPAIN)
    s = slots(); body = txt.format_map(s); tags = set(); body = noise(body, tags)
    pre = rng.choice(OPENERS[lang]); 
    tickets.append(dict(text=((pre + "\n\n") if pre and rng.random() < .5 else "") + body, lang=lang, when=with_time(rand_date(START, END)),
                        category=cat, themes=[], pains=[], flags=[], evidence=[], tags=tags, pii=[], severity=None,
                        sentiment="positive" if cat == "praise" else "neutral", dup_of=None))

# duplicates: 3 exact copies, 3 near-duplicates of English single-theme pain tickets
for t in tickets: t["uid"] = id(t)
base = [t for t in tickets if t["category"] == "pain" and t["lang"] == "en" and len(t["themes"]) == 1 and not t["pii"]]
for i, orig in enumerate(rng.sample(base, N_DUP_EXACT + N_DUP_NEAR)):
    exact = i < N_DUP_EXACT
    text = orig["text"] if exact else rng.choice(["REMINDER: " + orig["text"], orig["text"] + " Any update on this?", orig["text"] + " Please reply, this is urgent."])
    dup = dict(orig); dup.update(text=text, when=orig["when"] + dt.timedelta(days=rng.randint(1, 3), minutes=rng.randint(5, 600)),
                      tags=set(orig["tags"]) | {"duplicate_exact" if exact else "duplicate_near"}, dup_of=orig["uid"], uid=id(dup))
    dup["when"] = min(dup["when"], dt.datetime(2026, 10, 31, 23, 0)); tickets.append(dup)

tickets.sort(key=lambda t: t["when"])
uid2id = {}
for i, t in enumerate(tickets, 1): t["id"] = f"tkt_{i:04d}"; uid2id[t["uid"]] = t["id"]

# ---------- write ----------
def version(d):
    return "8.3.2" if d < REL else ("8.4.0" if d < FIX else "8.4.1")
PRI = {"low": "P4", "medium": "P3", "high": "P2", "critical": "P1"}
with open(OUT / "02_tickets/tickets.csv", "w", newline="", encoding="utf-8") as f, \
     open(OUT / "02_tickets/tickets_groundtruth.csv", "w", newline="", encoding="utf-8") as g:
    w = csv.writer(f); w.writerow(["id", "source", "date", "text", "metadata"])
    gw = csv.writer(g); gw.writerow(["id", "language", "category", "sentiment", "themes", "severity", "pain_points_json",
                                     "churn_flags", "churn_evidence_json", "tags", "pii_json", "duplicate_of"])
    for t in tickets:
        d = t["when"]; sev = t["severity"] or "low"
        pr = PRI[sev] if rng.random() > .15 else rng.choice(["P2", "P3", "P4"])
        age = (dt.datetime(2026, 11, 1) - d).days
        status = rng.choices(["Open", "In Progress", "Resolved", "Closed"], [.03, .05, .32, .6] if age > 21 else [.25, .3, .3, .15])[0]
        meta = dict(ticket_id=f"TKT-{10000 + int(t['id'][-4:]) * 7}", priority=pr, status=status,
                    channel=rng.choice(["email", "in_app_form", "in_app_form", "chat"]),
                    plan=rng.choice(["Free", "Premium Monthly", "Premium Annual", "Premium Plus"]),
                    platform=rng.choices(["Android", "iOS"], [.88, .12])[0], app_version=version(d.date()), city=rng.choice(CITIES))
        w.writerow([t["id"], "support_ticket", d.strftime("%Y-%m-%d %H:%M"), t["text"], json.dumps(meta, ensure_ascii=False)])
        gw.writerow([t["id"], t["lang"], t["category"], t["sentiment"], "|".join(t["themes"]), t["severity"] or "",
                     json.dumps(t["pains"], ensure_ascii=False), "|".join(t["flags"]), json.dumps(t["evidence"], ensure_ascii=False),
                     "|".join(sorted(t["tags"])), json.dumps([dict(type=a, value=b) for a, b in t["pii"]], ensure_ascii=False),
                     uid2id.get(t["dup_of"], "")])

with open(OUT / "02_tickets/events.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["date", "event", "type", "expected_effect"]); w.writerows(EVENTS)

# ---------- planted counts (duplicates excluded so these are the "true" unique counts) ----------
uniq = [t for t in tickets if not t["dup_of"]]
def week(d): return (d.date() - dt.timedelta(days=d.weekday())).isoformat()
counts = dict(
    total_tickets=len(tickets), unique_tickets=len(uniq), duplicates=len(tickets) - len(uniq),
    by_category=Counter(t["category"] for t in uniq),
    by_language=Counter(t["lang"] for t in uniq),
    by_theme={tid: sum(tid in t["themes"] for t in uniq) for tid in THEMES},
    by_issue=dict(Counter(p["issue_id"] for t in uniq for p in t["pains"])),
    by_churn_flag=dict(Counter(fl for t in uniq for fl in t["flags"])),
    tickets_with_pii=sum(bool(t["pii"]) for t in tickets),
    tags=dict(Counter(tag for t in tickets for tag in t["tags"])))
(OUT / "01_themes/planted_counts.json").write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")
weekly = defaultdict(Counter)
for t in uniq:
    for th in t["themes"]: weekly[week(t["when"])][th] += 1
with open(OUT / "01_themes/planted_trend_by_week.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["week_start"] + list(THEMES))
    for wk in sorted(weekly): w.writerow([wk] + [weekly[wk][th] for th in THEMES])

# themes.json (with planted counts embedded)
themes_out = []
for tid, v in THEMES.items():
    issues = [dict(issue_id=i, label=l, default_severity=s) for i, (th, l, s) in ISSUES.items() if th == tid]
    themes_out.append(dict(theme_id=tid, **v, planted_unique_tickets=counts["by_theme"][tid], issues=issues))
(OUT / "01_themes/themes.json").write_text(json.dumps(dict(
    app_context="Fictional wellness/fitness app modelled on HealthifyMe-style Indian users. App name is never used in the data.",
    churn_flags=CHURN_FLAGS, events=[dict(date=a, event=b, type=c, expected_effect=d) for a, b, c, d in EVENTS], themes=themes_out),
    indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: counts[k] for k in ["total_tickets", "unique_tickets", "by_theme", "by_language", "by_churn_flag", "tags"]}, indent=1))
