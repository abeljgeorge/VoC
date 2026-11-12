"""10 WhatsApp-style HTML chat renders (-> PNG via Playwright) + 5 scripts for real screenshots. Ground truth asserted verbatim."""
import json, os, html
from pathlib import Path
from content import ISSUES, THEMES

OUT = Path(__file__).resolve().parent.parent
FA = {t: v["feature_area"] for t, v in THEMES.items()}
C, S = "customer", "support"

RENDERS = [
 dict(id="chat_01", lang="en", mode="light", width=390, font=16, contact="FitApp Support", msgs=[
   (S, "10:02", "Hi, this is FitApp Support. How can we help you today?"),
   (C, "10:03", "Hi. I was charged twice for the Premium Annual plan today. Rs 2,999 got deducted two times."),
   (S, "10:05", "Sorry to hear that. Can you share the transaction IDs?"),
   (C, "10:06", "Both are from the same Google Pay account, 10 minutes apart. I have the SMS alerts."),
   (S, "10:09", "We will check and get back to you in 5 to 7 working days."),
   (C, "10:10", "5 to 7 days for your own mistake? I want my money back today.")],
   pains=[("double_charge", "I was charged twice for the Premium Annual plan today")], churn=[("refund_dispute", "I want my money back today")]),
 dict(id="chat_02", lang="hi-en", mode="dark", width=412, font=15, contact="FitApp Support", msgs=[
   (S, "18:20", "Namaste! FitApp Support mein aapka swagat hai."),
   (C, "18:21", "Maine plan cancel kiya tha pichle mahine phir bhi paise kat gaye."),
   (S, "18:22", "Kya aap apna registered number bata sakte hain?"),
   (C, "18:23", "Number hai 98765 43210. Cancel ka option app mein mila hi nahi, bahut dhundha."),
   (S, "18:25", "Hum check karke batate hain."),
   (C, "18:26", "Refund chahiye aur subscription turant band karo.")],
   pains=[("cancel_continues", "Maine plan cancel kiya tha pichle mahine phir bhi paise kat gaye"), ("cancel_not_found", "Cancel ka option app mein mila hi nahi")],
   churn=[("cancel_intent", "subscription turant band karo")], pii=[("PHONE_NUMBER", "98765 43210")]),
 dict(id="chat_03", lang="en", mode="light", width=360, font=15, contact="FitApp Support", msgs=[
   (C, "09:14", "Hi, my Fitbit stopped syncing steps after the update."),
   (S, "09:16", "Hello Rohit. Which app version are you on?"),
   (C, "09:17", "8.4.0. The app shows 0 steps but the watch shows 9,412 steps today."),
   (S, "09:20", "Please try reconnecting your device from Settings."),
   (C, "09:22", "I did that three times. It works for a day and then disconnects again."),
   (S, "09:24", "Noted. We have raised this with our tech team.")],
   pains=[("steps_not_syncing", "my Fitbit stopped syncing steps after the update"), ("reconnect_drops", "It works for a day and then disconnects again")], churn=[], pii=[("PERSON", "Rohit")]),
 dict(id="chat_04", lang="hi-en", mode="dark", width=390, font=16, contact="FitApp Support", msgs=[
   (C, "13:05", "Hi, ek problem hai. Poha ki calories 350 dikha raha hai, jabki ek plate mein 180 ke aaspaas hoti hai."),
   (S, "13:07", "Hum database check karenge. Aur koi issue?"),
   (C, "13:08", "Haan, roti ko size ya katori mein log karne ka option nahi hai, sirf grams."),
   (S, "13:10", "Ye feature request hum team ko bhej denge."),
   (C, "13:11", "Aur ghar ke dishes jaise bhindi masala search karo toh milta hi nahi.")],
   pains=[("wrong_calories", "Poha ki calories 350 dikha raha hai, jabki ek plate mein 180 ke aaspaas hoti hai"),
          ("portion_units", "roti ko size ya katori mein log karne ka option nahi hai, sirf grams"),
          ("missing_foods", "ghar ke dishes jaise bhindi masala search karo toh milta hi nahi")], churn=[]),
 dict(id="chat_05", lang="en", mode="light", width=412, font=16, contact="FitApp Support", msgs=[
   (C, "20:40", "Hello, I just installed the app but I am stuck on the first setup screen."),
   (S, "20:42", "Hi Meera, which step are you stuck on?"),
   (C, "20:43", "The Next button does nothing after I enter my weight. I had to reinstall twice."),
   (S, "20:45", "Sorry about that. Please update to the latest version."),
   (C, "20:47", "Also there are too many questions in setup. I do not understand what I am supposed to do each day.")],
   pains=[("setup_stuck", "The Next button does nothing after I enter my weight"), ("too_many_questions", "there are too many questions in setup"),
          ("unclear_plan_steps", "I do not understand what I am supposed to do each day")], churn=[], pii=[("PERSON", "Meera")]),
 dict(id="chat_06", lang="hi-en", mode="dark", width=360, font=15, contact="FitApp Support", msgs=[
   (C, "07:30", "OTP nahi aa raha, login nahi ho pa raha."),
   (S, "07:31", "Kitne time se try kar rahe hain?"),
   (C, "07:33", "2 din se try kar raha hu, 6 baar OTP maanga par ek bhi nahi aaya."),
   (S, "07:35", "Kya aap email se login try kar sakte hain?"),
   (C, "07:36", "Email se try kiya toh app open karte hi crash ho jata hai.")],
   pains=[("otp_not_received", "OTP nahi aa raha, login nahi ho pa raha"), ("crash_after_update", "app open karte hi crash ho jata hai")], churn=[]),
 dict(id="chat_07", lang="en", mode="light", width=390, font=16, contact="Coach Arjun", msgs=[
   (S, "11:00", "Hi Divya, here is your updated diet chart for this week."),
   (C, "11:12", "Thanks, but this is the same chart as last month."),
   (C, "11:13", "I messaged you on Monday about my knee pain and got a reply only today, Thursday."),
   (S, "11:20", "Sorry, I was handling many clients."),
   (C, "11:22", "For Rs 8,000 I expected daily check-ins. I might cancel and try Cult.fit instead.")],
   pains=[("coach_generic", "this is the same chart as last month"), ("coach_slow", "I messaged you on Monday about my knee pain and got a reply only today, Thursday")],
   churn=[("cancel_intent", "I might cancel and try Cult.fit instead"), ("competitor_mention", "I might cancel and try Cult.fit instead")], pii=[("PERSON", "Divya")]),
 dict(id="chat_08", lang="hi-en", mode="dark", width=412, font=16, contact="FitApp Support", msgs=[
   (C, "16:15", "Mera diet plan galat lag raha hai, main strictly vegetarian hu."),
   (S, "16:17", "Kya hua? Plan mein kya dikh raha hai?"),
   (C, "16:18", "Dinner mein baar baar egg curry aur chicken soup suggest kar raha hai."),
   (S, "16:20", "Hum aapka preference update kar dete hain."),
   (C, "16:21", "Pehle bhi 2 baar update kiya tha, plan wahi aa raha hai.")],
   pains=[("veg_plan", "Dinner mein baar baar egg curry aur chicken soup suggest kar raha hai")], churn=[]),
 dict(id="chat_09", lang="en", mode="light", width=360, font=15, contact="FitApp Support", msgs=[
   (C, "12:30", "Hi, my free trial was 7 days but Rs 1,499 got charged on day 6."),
   (S, "12:33", "Hello Arjun, we are checking this."),
   (C, "12:34", "I also tried to cancel but there is no cancel button in the app anywhere."),
   (S, "12:36", "Please cancel through the Google Play subscriptions page."),
   (C, "12:38", "Why does the app not say that? Anyway, refund the money or I will raise a dispute with my bank.")],
   pains=[("charged_after_trial", "my free trial was 7 days but Rs 1,499 got charged on day 6"), ("cancel_not_found", "there is no cancel button in the app anywhere")],
   churn=[("refund_dispute", "I will raise a dispute with my bank")], pii=[("PERSON", "Arjun")]),
 dict(id="chat_10", lang="en", mode="dark", width=390, font=16, contact="FitApp Support", msgs=[
   (C, "15:02", "Hi! Can I use one subscription on two phones?"),
   (S, "15:04", "Yes, you can log in on up to 2 devices with the same account."),
   (C, "15:05", "Great, thanks. By the way I love the new workout tracker, lost 4 kg already!"),
   (S, "15:06", "That is wonderful to hear, congratulations!"),
   (C, "15:08", "One request: please add a water reminder widget.")],
   pains=[], churn=[], note="No pain points: question + praise + feature request. Tests precision (nothing should be flagged)."),
]

REAL = [
 dict(id="real_01", lang="en", contact="FitApp Support", msgs=[
   (C, "Hi, my payment failed in the app but Rs 2,999 was debited from my bank account."),
   (S, "Sorry about that. Is your premium active now?"),
   (C, "No, premium is still not active. It has been 3 days."),
   (S, "We will look into it and revert."),
   (C, "Please refund it if you cannot activate the plan.")],
   pains=[("failed_payment_debited", "my payment failed in the app but Rs 2,999 was debited from my bank account")], churn=[]),
 dict(id="real_02", lang="hi-en", contact="FitApp Support", msgs=[
   (C, "Bhai, update ke baad Mi Band ka sleep data app mein aa hi nahi raha."),
   (S, "Steps sync ho rahe hain kya?"),
   (C, "Steps double count ho rahe hain, ek phone se aur ek band se."),
   (S, "Hmm, ye pehli baar sun raha hu."),
   (C, "Ye fix nahi hua toh main app uninstall kar dunga.")],
   pains=[("sleep_missing", "update ke baad Mi Band ka sleep data app mein aa hi nahi raha"), ("duplicate_steps", "Steps double count ho rahe hain, ek phone se aur ek band se")],
   churn=[("uninstall", "main app uninstall kar dunga")]),
 dict(id="real_03", lang="en", contact="FitApp Support", msgs=[
   (C, "Hello, my refund was approved 12 days ago and I still have not received the money."),
   (S, "Refunds can take 7 to 10 working days."),
   (C, "It has already been more than that. Nobody gives me a proper update."),
   (S, "Let me escalate it."),
   (C, "If I do not get it by Friday I will file a chargeback with my bank.")],
   pains=[("refund_delay", "my refund was approved 12 days ago and I still have not received the money")], churn=[("refund_dispute", "I will file a chargeback with my bank")]),
 dict(id="real_04", lang="hi-en", contact="FitApp Support", msgs=[
   (C, "Barcode scan karne par har baar product not found aata hai."),
   (S, "Kaunsa product scan kar rahe ho?"),
   (C, "Biscuit aur chips jaise packaged items bhi nahi milte."),
   (S, "Manually add kar lo abhi."),
   (C, "Manually add karna hi hota toh scan feature kyu rakha hai.")],
   pains=[("barcode_fail", "Barcode scan karne par har baar product not found aata hai")], churn=[]),
 dict(id="real_05", lang="hi-en", contact="FitApp Support", msgs=[
   (C, "Signup ke turant baad paywall aa gaya, app kya karta hai wo samajhne se pehle hi."),
   (S, "Free trial option bhi dikha hoga na?"),
   (C, "Haan par pehle app dekhne ko to mile, itna pressure kyun."),
   (S, "Hum feedback team ko bhej denge."),
   (C, "Competition mein cult.fit aisa nahi karta, free mein dikha deta hai.")],
   pains=[("paywall_early", "Signup ke turant baad paywall aa gaya, app kya karta hai wo samajhne se pehle hi")],
   churn=[("competitor_mention", "cult.fit aisa nahi karta, free mein dikha deta hai")]),
]

def pain_records(c, text):
    out = []
    for iid, q in c["pains"]:
        assert q in text, (c["id"], q); th, label, sev = ISSUES[iid]
        out.append(dict(issue_id=iid, issue=label, theme_id=th, feature_area=FA[th], severity=sev, quote=q))
    for _, q in c["churn"]: assert q in text, (c["id"], q)
    for _, v in c.get("pii", []): assert v in text, (c["id"], v)
    return out

def render_html(c):
    dark = c["mode"] == "dark"
    bg, hdr, inb, outb, txt, sub, tick = (("#0b141a", "#1f2c34", "#202c33", "#005c4b", "#e9edef", "#8696a0", "#53bdeb") if dark
                                          else ("#efeae2", "#008069", "#ffffff", "#d9fdd3", "#111b21", "#667781", "#53bdeb"))
    rows = ""
    for who, t, m in c["msgs"]:
        cls = "out" if who == C else "in"
        ticks = '<span class="tk">&#10003;&#10003;</span>' if who == C else ""
        rows += f'<div class="row {cls}"><div class="b">{html.escape(m)}<span class="meta">{t}{ticks}</span></div></div>\n'
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box}}body{{margin:0;width:{c['width']}px;background:{bg};font-family:Roboto,'Helvetica Neue',Arial,sans-serif;color:{txt}}}
.hdr{{background:{hdr};color:#fff;padding:12px 14px;display:flex;align-items:center;gap:12px}}
.av{{width:36px;height:36px;border-radius:50%;background:#6b7c85}}.nm{{font-size:17px;font-weight:500}}.on{{font-size:12px;opacity:.8}}
.chat{{padding:12px 10px 18px}}.chip{{margin:6px auto 12px;width:max-content;background:{inb};color:{sub};font-size:12px;padding:5px 10px;border-radius:8px}}
.row{{display:flex;margin:3px 0}}.row.out{{justify-content:flex-end}}
.b{{max-width:80%;padding:6px 8px 4px 9px;border-radius:8px;font-size:{c['font']}px;line-height:1.3;background:{inb};box-shadow:0 1px .5px rgba(0,0,0,.13)}}
.out .b{{background:{outb}}}.meta{{float:right;margin:6px 0 0 10px;font-size:11px;color:{sub}}}.tk{{color:{tick};margin-left:3px}}
.bar{{margin:14px 6px 0;background:{inb};border-radius:22px;padding:11px 16px;color:{sub};font-size:15px}}
</style></head><body>
<div class="hdr"><span>&#8592;</span><div class="av"></div><div><div class="nm">{html.escape(c['contact'])}</div><div class="on">online</div></div></div>
<div class="chat"><div class="chip">TODAY</div>
{rows}<div class="bar">Message</div></div></body></html>"""

gt = []
for c in RENDERS:
    text = "\n".join(m for _, _, m in c["msgs"]); pains = pain_records(c, text)
    (OUT / "04_screenshots/renders" / f"{c['id']}.html").write_text(render_html(c), encoding="utf-8")
    gt.append(dict(id=c["id"], source="screenshot_render", image=f"renders/{c['id']}.png", language=c["lang"], theme=c["mode"] and None,
                   themes=list(dict.fromkeys(p["theme_id"] for p in pains)), pain_points=pains,
                   churn_evidence=[dict(flag=f, quote=q) for f, q in c["churn"]], pii=[dict(type=a, value=b) for a, b in c.get("pii", [])],
                   style=dict(mode=c["mode"], width=c["width"], font_px=c["font"]), note=c.get("note", ""),
                   messages=[dict(sender=w, time=t, text=m) for w, t, m in c["msgs"]],
                   ocr_reference="\n".join(f"{t} {m}" for _, t, m in c["msgs"])))
for g in gt: g.pop("theme", None)
(OUT / "04_screenshots/screenshots_groundtruth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")

# real scripts
rg, md = [], ["# Real WhatsApp screenshot scripts (5)", "",
              "Goal: about 5 real screenshots of messy, real-world layouts to test OCR beyond the clean HTML renders.", "",
              "## How to capture", "- Use two WhatsApp numbers (or you + a friend). **You** send the *customer* lines, the other person sends the *support* lines.",
              "- Type the lines exactly as written. Do not fix Hinglish spelling.",
              "- Vary the conditions on purpose: dark mode for 2 of them, one with a wallpaper, one scrolled mid-chat, one slightly cropped, one at low brightness.",
              "- Take a normal phone screenshot. Save as `real_01.png` ... `real_05.png` into `04_screenshots/real/`.",
              "- Change the contact name to `FitApp Support` and blur nothing: all numbers and names here are fake.", ""]
for r in REAL:
    text = "\n".join(m for _, m in r["msgs"]); pains = pain_records(r, text)
    rg.append(dict(id=r["id"], source="screenshot_real", image=f"real/{r['id']}.png", language=r["lang"], themes=list(dict.fromkeys(p["theme_id"] for p in pains)),
                   pain_points=pains, churn_evidence=[dict(flag=f, quote=q) for f, q in r["churn"]], messages=[dict(sender=w, text=m) for w, m in r["msgs"]],
                   ocr_reference="\n".join(m for _, m in r["msgs"])))
    md += [f"## {r['id']}  ({r['lang']})", ""] + [f"- **{'You (customer)' if w == C else 'Other person (support)'}:** {m}" for w, m in r["msgs"]] + [""]
(OUT / "04_screenshots/real_whatsapp_scripts.md").write_text("\n".join(md), encoding="utf-8")
(OUT / "04_screenshots/real_screenshots_groundtruth.json").write_text(json.dumps(rg, indent=2, ensure_ascii=False), encoding="utf-8")

# render PNGs
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        for c in RENDERS:
            pg = b.new_page(viewport={"width": c["width"], "height": 300}, device_scale_factor=2)
            pg.goto((OUT / "04_screenshots/renders" / f"{c['id']}.html").as_uri()); pg.screenshot(path=str(OUT / "04_screenshots/renders" / f"{c['id']}.png"), full_page=True); pg.close()
        b.close()
    print("rendered", len(RENDERS), "PNGs")
except Exception as e:
    print("PNG render skipped:", e)
print("chats ok:", len(RENDERS), "renders,", len(REAL), "real scripts")
