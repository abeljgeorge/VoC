"""Quick Tesseract baseline on the HTML chat renders: character similarity vs ocr_reference (timestamps ignored)."""
import json, re, difflib, subprocess
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent / "04_screenshots"
norm = lambda s: re.sub(r"\s+", " ", re.sub(r"\b\d{1,2}:\d{2}\b|[\u2713]", "", s)).strip().lower()
scores = []
for it in json.load(open(OUT / "screenshots_groundtruth.json")):
    txt = subprocess.run(["tesseract", str(OUT / it["image"]), "-", "--psm", "6"], capture_output=True, text=True).stdout
    ref = norm(" ".join(m["text"] for m in it["messages"]))
    sim = difflib.SequenceMatcher(None, norm(txt), ref, autojunk=False).ratio(); scores.append(sim)
    print(f'{it["id"]}: similarity {sim:.2f}')
print(f"mean similarity {sum(scores)/len(scores):.2f}")
