"""Mock interview scripts (to be recorded by you) + ground truth. Asserts every planted quote appears verbatim."""
import json
from pathlib import Path
from content import ISSUES, THEMES

OUT = Path(__file__).resolve().parent.parent
FA = {t: v["feature_area"] for t, v in THEMES.items()}

INTERVIEWS = [
 dict(id="int_01", persona="Priya, 29, software engineer, Bengaluru", language="en", minutes="1-2",
  turns=[
   ("INTERVIEWER", "Thanks for joining, Priya. Can you tell me how you started using the app?"),
   ("PRIYA", "Sure. I signed up in July after a colleague recommended it. I took the seven day free trial because I wanted to see if the meal logging was actually any good."),
   ("INTERVIEWER", "And how did the trial go?"),
   ("PRIYA", "The trial was fine, honestly. The problem started after that. I was charged Rs 1,499 on day six, a full day before the trial was supposed to end. Nobody warned me, there was no email, nothing."),
   ("INTERVIEWER", "What did you do when you noticed?"),
   ("PRIYA", "I tried to cancel immediately. But I could not find the cancel option anywhere in the app. I went through settings, profile, even the help section. In the end I had to Google how to cancel, and it sent me to the Play Store."),
   ("INTERVIEWER", "Did you contact support?"),
   ("PRIYA", "Yes, and that was another round of waiting. They said refunds are only possible within 48 hours, and by the time they replied it was day three. So I got a no."),
   ("INTERVIEWER", "How did that make you feel about the app?"),
   ("PRIYA", "Honestly, it felt like a trap. I would have happily paid after the trial if I liked it. Now I just want my money back, and if I do not get it I will file a dispute with my bank. I have already deleted the app from my phone."),
   ("INTERVIEWER", "Was there anything you liked?"),
   ("PRIYA", "The food diary is nice and simple, I will give it that."),
  ],
  pains=[("charged_after_trial", "I was charged Rs 1,499 on day six, a full day before the trial was supposed to end"),
         ("cancel_not_found", "I could not find the cancel option anywhere in the app"),
         ("refund_denied", "They said refunds are only possible within 48 hours")],
  churn=[("cancel_intent", "I tried to cancel immediately"), ("refund_dispute", "I will file a dispute with my bank"),
         ("uninstall", "I have already deleted the app from my phone")],
  positives=["The food diary is nice and simple"]),
 dict(id="int_02", persona="Rahul, 34, sales manager, Pune", language="hi-en", minutes="1-2",
  turns=[
   ("INTERVIEWER", "Rahul, thoda batao, aap app kaise use karte ho?"),
   ("RAHUL", "Haan, main roz subah daily steps aur khana log karta hu. Mi Band 6 hai mere paas, usse sync karta hu app ko."),
   ("INTERVIEWER", "Sync ka experience kaisa raha?"),
   ("RAHUL", "Pehle sab theek tha, par pichle update ke baad steps sync hi nahi ho rahe. App mein zero dikhata hai jabki band mein aath hazaar se zyada steps hote hain. Do hafte se aisa chal raha hai."),
   ("INTERVIEWER", "Phir aapne kya kiya?"),
   ("RAHUL", "Maine band dobara pair kiya, Google Fit bhi reconnect kiya, par ek din chalta hai aur phir disconnect ho jata hai. Bahut frustrating hai."),
   ("INTERVIEWER", "Aur food logging ka?"),
   ("RAHUL", "Wahan bhi problem hai. Dal chawal ya paratha jaisi cheezein log karta hu toh calories bahut galat dikhati hain. Ek paratha ke liye 450 kcal bata raha tha, jabki ghar ka paratha mere hisaab se 250 ke aaspaas hoga. Aur katori ke hisaab se log karne ka option bhi nahi hai, sirf grams."),
   ("INTERVIEWER", "Kabhi koi aur app try kiya?"),
   ("RAHUL", "Haan, mere dost Fittr use karta hai, uska tracking zyada accurate lagta hai. Ab main Fittr pe shift hone ka soch raha hu."),
   ("INTERVIEWER", "Last mein kuch accha laga?"),
   ("RAHUL", "Workout ideas achhe hain, wo pasand aaye."),
  ],
  pains=[("steps_not_syncing", "pichle update ke baad steps sync hi nahi ho rahe"),
         ("reconnect_drops", "ek din chalta hai aur phir disconnect ho jata hai"),
         ("wrong_calories", "Ek paratha ke liye 450 kcal bata raha tha, jabki ghar ka paratha mere hisaab se 250 ke aaspaas hoga"),
         ("portion_units", "katori ke hisaab se log karne ka option bhi nahi hai, sirf grams")],
  churn=[("competitor_mention", "Ab main Fittr pe shift hone ka soch raha hu")],
  positives=["Workout ideas achhe hain"]),
 dict(id="int_03", persona="Anita, 45, school teacher, Hyderabad", language="en", minutes="1-2",
  turns=[
   ("INTERVIEWER", "Anita, how did you first start with the app?"),
   ("ANITA", "My doctor suggested I lose some weight, and my daughter installed the app for me. I am not very comfortable with technology, so I was nervous."),
   ("INTERVIEWER", "What was the first experience like?"),
   ("ANITA", "Honestly confusing. The setup asked me so many questions, about twenty I think, that I gave up halfway the first time. And then right after I signed up, a payment screen popped up before I even understood what the app does."),
   ("INTERVIEWER", "Did you figure out the goal setting?"),
   ("ANITA", "Not really. I could not figure out how to set my weight loss goal. The first screen does not explain what to do next. My daughter had to sit with me and do it."),
   ("INTERVIEWER", "What about the meal plan?"),
   ("ANITA", "That is my bigger problem. I am diabetic, and the meal plan keeps suggesting sweet things like fruit smoothies and honey oats. There is no way to tell the app about my condition. I also eat only vegetarian food, and it still showed me an egg recipe once."),
   ("INTERVIEWER", "Would you recommend it?"),
   ("ANITA", "Maybe to my younger relatives. For someone like me, it needs to be much simpler, and it should understand medical conditions. The reminders are nice though."),
  ],
  pains=[("too_many_questions", "The setup asked me so many questions, about twenty I think, that I gave up halfway the first time"),
         ("paywall_early", "a payment screen popped up before I even understood what the app does"),
         ("goal_unclear", "I could not figure out how to set my weight loss goal"),
         ("diabetic_plan", "I am diabetic, and the meal plan keeps suggesting sweet things like fruit smoothies and honey oats"),
         ("veg_plan", "I also eat only vegetarian food, and it still showed me an egg recipe once")],
  churn=[], positives=["The reminders are nice though"]),
 dict(id="int_04", persona="Karthik, 26, product analyst, Chennai", language="hi-en (light code-mixing)", minutes="1-2",
  turns=[
   ("INTERVIEWER", "Karthik, tell me about the last time you opened the app."),
   ("KARTHIK", "Yaar, last week I tried to log in after changing my phone and the OTP never came. I tried like five times over two days. Finally I used the email option, and then I got logged out again the next morning."),
   ("INTERVIEWER", "That sounds annoying. What else?"),
   ("KARTHIK", "The coach part. I pay for a personal coach, Rs 6,000 for three months, but the replies take two to three days. For this price I expected daily check-ins. And the diet chart is the same generic thing they send everybody."),
   ("INTERVIEWER", "Did you ever raise it with them?"),
   ("KARTHIK", "I messaged the coach twice, same pattern. Honestly I think the premium plan is not worth the money. Strava gives me my run tracking for free and works better."),
   ("INTERVIEWER", "Are you still using the app?"),
   ("KARTHIK", "I uninstalled it yesterday. Maybe I will come back if the coach thing improves."),
   ("INTERVIEWER", "Anything you liked?"),
   ("KARTHIK", "The workout library was good, no complaints there."),
  ],
  pains=[("otp_not_received", "the OTP never came. I tried like five times over two days"),
         ("logged_out", "I got logged out again the next morning"),
         ("coach_slow", "the replies take two to three days"),
         ("coach_generic", "the diet chart is the same generic thing they send everybody"),
         ("price_value", "I think the premium plan is not worth the money")],
  churn=[("competitor_mention", "Strava gives me my run tracking for free and works better"), ("uninstall", "I uninstalled it yesterday")],
  positives=["The workout library was good"]),
]

gt = []
for iv in INTERVIEWS:
    transcript = "\n".join(f"{s}: {t}" for s, t in iv["turns"])
    pains = []
    for iid, q in iv["pains"]:
        assert q in transcript, (iv["id"], q)
        th, label, sev = ISSUES[iid]
        pains.append(dict(issue_id=iid, issue=label, theme_id=th, feature_area=FA[th], severity=sev, quote=q))
    for fl, q in iv["churn"]: assert q in transcript, (iv["id"], q)
    for q in iv["positives"]: assert q in transcript, (iv["id"], q)
    themes = list(dict.fromkeys(p["theme_id"] for p in pains))
    words = len(" ".join(t for s, t in iv["turns"]).split())
    gt.append(dict(id=iv["id"], source="interview", persona=iv["persona"], language=iv["language"], themes=themes, pain_points=pains,
                   churn_evidence=[dict(flag=f, quote=q) for f, q in iv["churn"]], positives=iv["positives"], transcript=transcript, word_count=words))
    md = [f"# {iv['id']} - {iv['persona']}", "",
          f"**Language:** {iv['language']}  |  **Target length:** {iv['minutes']} minutes  |  **Words:** {words}", "",
          "## Recording notes",
          "- Record both roles yourself or with a friend. Speak naturally at your normal pace; small ad-libs are fine.",
          "- Use your own accent. Do not clean up Hinglish words, they are the test.",
          "- Save as `" + iv["id"] + ".wav` or `.m4a` (mono is fine). Hand-correct the Whisper transcript later to get the WER reference.",
          "- Ground truth for this clip is in `interviews_groundtruth.json`. Do not show it to the pipeline.", "",
          "## Script", ""]
    md += [f"**{s}:** {t}\n" for s, t in iv["turns"]]
    (OUT / "03_interviews/scripts" / f"{iv['id']}.md").write_text("\n".join(md), encoding="utf-8")
(OUT / "03_interviews/interviews_groundtruth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
print("interviews ok:", [(g["id"], g["word_count"], len(g["pain_points"])) for g in gt])
