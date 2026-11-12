"""Shared content for the VoC Copilot synthetic data generators.

Everything the pipeline should FIND is defined here (themes -> issues -> text fragments).
Generators compose tickets / interviews / chats from these, so ground truth is exact by construction.
"""

THEMES = {
    "T01": dict(name="Unexpected subscription charges", feature_area="billing", frequency="high",
                description="Customers charged twice, charged before trial ends, auto-renewed without notice, or charged more than shown.",
                expected_churn_flags=["refund_dispute"]),
    "T02": dict(name="Cancellation and refund friction", feature_area="billing", frequency="high",
                description="Cannot find how to cancel, conflicting instructions, refunds denied or delayed, charged after cancelling.",
                expected_churn_flags=["cancel_intent", "refund_dispute"]),
    "T03": dict(name="Food logging and calorie inaccuracy", feature_area="food_tracking", frequency="high",
                description="Wrong calories for Indian dishes, no katori/roti units, missing home-cooked foods, barcode scan failures.",
                expected_churn_flags=["competitor_mention"]),
    "T04": dict(name="Wearable and step sync failures", feature_area="device_sync", frequency="high (spike)",
                description="Steps/sleep not syncing from bands and watches, Google Fit disconnecting. Spikes after release 8.4.0, drops after hotfix 8.4.1.",
                expected_churn_flags=["uninstall", "competitor_mention"]),
    "T05": dict(name="Onboarding and setup confusion", feature_area="onboarding", frequency="medium",
                description="Too many setup questions, unclear goal setting, paywall before value, stuck on first step.",
                expected_churn_flags=["uninstall"]),
    "T06": dict(name="Login, OTP and app stability", feature_area="login_stability", frequency="medium (spike)",
                description="OTP never arrives, crashes after update, repeated logouts, slow loading. Small spike right after release 8.4.0.",
                expected_churn_flags=["uninstall"]),
    "T07": dict(name="Coach responsiveness and value for price", feature_area="coaching", frequency="low",
                description="Slow coach replies, generic diet charts, premium not worth the price.",
                expected_churn_flags=["cancel_intent", "competitor_mention"]),
    "T08": dict(name="Diet plan does not fit my needs", feature_area="personalization", frequency="rare",
                description="Plans ignore diabetes, vegetarian preference or regional cuisine. Deliberately rare to test long-tail detection.",
                expected_churn_flags=[]),
}

# issue_id -> (theme, canonical issue label, default severity)
ISSUES = {
    "double_charge": ("T01", "Charged twice for the same plan", "high"),
    "charged_after_trial": ("T01", "Charged before the free trial ended", "high"),
    "renewal_without_notice": ("T01", "Auto-renewal with no reminder", "high"),
    "price_mismatch": ("T01", "Charged more than the price shown", "medium"),
    "failed_payment_debited": ("T01", "Payment failed but money was debited", "high"),
    "hidden_taxes": ("T01", "Extra charges not shown at checkout", "medium"),
    "cancel_not_found": ("T02", "Cannot find how to cancel in the app", "high"),
    "cancel_redirect": ("T02", "Conflicting cancellation instructions", "medium"),
    "refund_denied": ("T02", "Refund request refused", "high"),
    "refund_delay": ("T02", "Approved refund not received", "high"),
    "cancel_continues": ("T02", "Charged again after cancelling", "high"),
    "wrong_calories": ("T03", "Calorie values wrong for Indian dishes", "medium"),
    "portion_units": ("T03", "No katori/roti portion units", "medium"),
    "missing_foods": ("T03", "Home-cooked dishes missing from database", "medium"),
    "duplicate_entries": ("T03", "Many conflicting entries for one food", "low"),
    "barcode_fail": ("T03", "Barcode scan does not recognise products", "medium"),
    "macro_mismatch": ("T03", "Macros do not add up to calories", "medium"),
    "steps_not_syncing": ("T04", "Steps not syncing from wearable", "high"),
    "sync_delay": ("T04", "Wearable sync delayed by hours", "medium"),
    "reconnect_drops": ("T04", "Google Fit connection keeps dropping", "high"),
    "sleep_missing": ("T04", "Sleep data missing after update", "medium"),
    "duplicate_steps": ("T04", "Steps counted twice after sync", "medium"),
    "too_many_questions": ("T05", "Setup asks too many questions", "medium"),
    "goal_unclear": ("T05", "Cannot work out how to set a goal", "medium"),
    "paywall_early": ("T05", "Paywall shown before value is clear", "medium"),
    "setup_stuck": ("T05", "Stuck on first setup step", "high"),
    "unclear_plan_steps": ("T05", "No guidance on what to do each day", "medium"),
    "otp_not_received": ("T06", "OTP login code never arrives", "high"),
    "crash_after_update": ("T06", "App crashes on launch after update", "critical"),
    "logged_out": ("T06", "Repeated logouts lose the day's log", "high"),
    "slow_load": ("T06", "Home screen very slow to load", "medium"),
    "coach_slow": ("T07", "Coach replies take days", "medium"),
    "coach_generic": ("T07", "Generic copy-pasted diet chart", "medium"),
    "price_value": ("T07", "Premium not worth the price", "medium"),
    "diabetic_plan": ("T08", "Meal plan ignores diabetes", "high"),
    "veg_plan": ("T08", "Vegetarian preference ignored", "medium"),
    "regional_plan": ("T08", "No regional (South Indian) meal options", "low"),
}

CHURN_FLAGS = ["cancel_intent", "refund_dispute", "competitor_mention", "uninstall"]

# Fragment: (issue_id, lang, text, churn_flags, sarcasm). Slots: {amt} {amtlow} {day} {d} {dn} {plan} {device} {steps} {food} {c1} {c2} {home}
def _f(issue, lang, text, flags=(), sar=False):
    return dict(issue=issue, lang=lang, x=text, flags=list(flags), sar=sar)

FRAGMENTS = [
    # ---------------- T01 ----------------
    _f("double_charge", "en", "I was charged twice for the same {plan} plan this month. Rs {amt} was deducted two times from my account.", ["refund_dispute"]),
    _f("double_charge", "en", "Two identical payments of Rs {amt} went out for one {plan} subscription."),
    _f("double_charge", "hi-en", "Mere account se Rs {amt} do baar kat gaye, ek hi plan ke liye. Ye kya scene hai?", ["refund_dispute"]),
    _f("double_charge", "hi", "मेरे खाते से एक ही प्लान के लिए दो बार पैसे कट गए। कृपया रिफंड करें।", ["refund_dispute"]),
    _f("double_charge", "en", "Great job charging me twice for one plan. Really appreciate the surprise deduction of Rs {amt}.", ["refund_dispute"], True),
    _f("charged_after_trial", "en", "My free trial was supposed to last 7 days but I got charged Rs {amt} on day {day}.", ["refund_dispute"]),
    _f("charged_after_trial", "en", "The trial ended earlier than promised and Rs {amt} was taken from my card without any warning."),
    _f("charged_after_trial", "hi-en", "Free trial 7 din ka bola tha lekin {day}th din hi Rs {amt} kat liye. Bilkul galat hai.", ["refund_dispute"]),
    _f("renewal_without_notice", "en", "The annual plan auto-renewed and I got no reminder at all. Rs {amt} gone from my card just like that."),
    _f("renewal_without_notice", "hi-en", "Auto-renewal ka koi message nahi aaya, seedha Rs {amt} deduct ho gaye annual plan ke."),
    _f("price_mismatch", "en", "The price shown on the paywall was Rs {amtlow} but the final amount charged was Rs {amt}."),
    _f("price_mismatch", "hi-en", "Paywall pe Rs {amtlow} dikhaya tha par final amount Rs {amt} charge hua."),
    _f("failed_payment_debited", "en", "Payment failed in the app but the money was debited from my bank and my premium is still not active.", ["refund_dispute"]),
    _f("failed_payment_debited", "hi-en", "Payment fail dikha raha tha par bank se paise kat gaye, premium abhi bhi activate nahi hua.", ["refund_dispute"]),
    _f("hidden_taxes", "en", "Extra taxes were added at checkout that were never shown earlier. Feels misleading."),
    # ---------------- T02 ----------------
    _f("cancel_not_found", "en", "I cannot find any option to cancel my subscription inside the app. I have looked through settings three times.", ["cancel_intent"]),
    _f("cancel_not_found", "hi-en", "Subscription cancel karne ka option app mein mil hi nahi raha, settings mein 3 baar dekha.", ["cancel_intent"]),
    _f("cancel_not_found", "en", "Love how the cancel button is hidden so well. Must be a treasure hunt.", ["cancel_intent"], True),
    _f("cancel_redirect", "en", "Support keeps telling me to cancel from Google Play but the app says to cancel on your website. Nobody gives a straight answer.", ["cancel_intent"]),
    _f("refund_denied", "en", "I asked for a refund within 2 days of renewal and was told it is not possible. This is not fair for an unused plan.", ["refund_dispute"]),
    _f("refund_denied", "hi-en", "Renewal ke 2 din ke andar refund maanga par support ne mana kar diya. Plan use bhi nahi kiya tha.", ["refund_dispute"]),
    _f("refund_delay", "en", "My refund was approved {d} days ago and I still have not received the money.", ["refund_dispute"]),
    _f("refund_delay", "hi-en", "Refund approve hue {d} din ho gaye par paise abhi tak account mein nahi aaye.", ["refund_dispute"]),
    _f("cancel_continues", "en", "I cancelled my plan last month but I have been charged again.", ["cancel_intent", "refund_dispute"]),
    _f("cancel_continues", "hi-en", "Maine plan cancel kiya tha phir bhi agle mahine paise kat gaye. Refund chahiye.", ["cancel_intent", "refund_dispute"]),
    _f("cancel_continues", "hi", "मैंने सब्सक्रिप्शन रद्द किया था फिर भी इस महीने पैसे कट गए।", ["cancel_intent", "refund_dispute"]),
    # ---------------- T03 ----------------
    _f("wrong_calories", "en", "The calorie count for {food} is way off. The database shows {c1} kcal but a normal serving is closer to {c2}."),
    _f("wrong_calories", "hi-en", "{food} ki calories bahut galat dikha raha hai, {c1} kcal bata raha hai jabki ek serving mein lagbhag {c2} hoti hai."),
    _f("portion_units", "en", "There is no option to log a katori or a roti by size, only grams, so my logging is never accurate."),
    _f("portion_units", "hi-en", "Roti ya katori ke hisaab se log karne ka option hi nahi hai, sirf grams. Kaafi irritating hai."),
    _f("missing_foods", "en", "I cannot find many home cooked Indian dishes like {home}. I have to enter everything manually."),
    _f("missing_foods", "hi-en", "Ghar ka khana jaise {home} app mein milta hi nahi, har baar manually add karna padta hai."),
    _f("duplicate_entries", "en", "Searching for {food} shows ten different entries with ten different calorie values. Which one is right?"),
    _f("barcode_fail", "en", "Barcode scan does not recognise most packaged items I buy, it just says product not found."),
    _f("barcode_fail", "hi-en", "Barcode scan karne par product not found aata hai, packaged cheezein bhi nahi milti."),
    _f("macro_mismatch", "en", "My daily macros do not add up. Total calories do not match the protein, carbs and fat shown."),
    _f("wrong_calories", "hi", "{food} की कैलोरी बहुत गलत दिखा रहा है, ऐप में {c1} kcal है जबकि असल में {c2} के आसपास होती है।"),
    # ---------------- T04 ----------------
    _f("steps_not_syncing", "en", "Steps from my {device} stopped syncing after the latest update. The app shows zero steps while the watch shows over {steps}."),
    _f("steps_not_syncing", "en", "Since the update my {device} steps do not sync at all, the app keeps showing 0."),
    _f("steps_not_syncing", "hi-en", "Latest update ke baad {device} se steps sync nahi ho rahe. App mein zero dikha raha hai jabki watch mein {steps} se zyada hain."),
    _f("steps_not_syncing", "hi", "अपडेट के बाद मेरे बैंड से स्टेप्स सिंक नहीं हो रहे हैं।"),
    _f("steps_not_syncing", "en", "Wow, thanks for the update that made all my steps disappear. Truly a feature.", [], True),
    _f("sync_delay", "en", "Sync with {device} takes hours. My workouts appear the next day, which defeats the whole point of tracking."),
    _f("sync_delay", "hi-en", "{device} ka sync ghanto lagata hai, workout agle din dikhta hai."),
    _f("reconnect_drops", "en", "The Google Fit connection keeps dropping. I reconnect and it works for a day, then disconnects again."),
    _f("reconnect_drops", "hi-en", "Google Fit connect karta hu toh ek din chalta hai, phir apne aap disconnect ho jata hai."),
    _f("sleep_missing", "en", "Sleep data from my {device} is not showing in the app at all since the update."),
    _f("sleep_missing", "hi-en", "Update ke baad {device} ka sleep data app mein aa hi nahi raha."),
    _f("duplicate_steps", "en", "After syncing, my steps are counted twice, once from the phone and once from the band."),
    _f("duplicate_steps", "hi-en", "Steps double count ho rahe hain, ek phone se aur ek band se."),
    # ---------------- T05 ----------------
    _f("too_many_questions", "en", "The setup asks way too many questions before showing anything useful. I gave up halfway."),
    _f("too_many_questions", "hi-en", "Setup mein itne saare sawaal hain ki beech mein hi chhod diya."),
    _f("too_many_questions", "hi", "ऐप में सेटअप बहुत लंबा है, बीच में ही छोड़ दिया।"),
    _f("goal_unclear", "en", "I could not figure out how to set my weight loss goal. The first screen does not explain what to do next."),
    _f("goal_unclear", "hi-en", "Goal set kaise karna hai samajh nahi aaya, pehli screen pe kuch explain hi nahi kiya."),
    _f("paywall_early", "en", "Right after signup I hit a paywall before I even understood what the app does.", ["uninstall"]),
    _f("paywall_early", "hi-en", "Signup ke turant baad paywall aa gaya, app kya karta hai ye samajhne se pehle hi."),
    _f("paywall_early", "en", "Thanks for the paywall right after signup, so welcoming.", [], True),
    _f("setup_stuck", "en", "I got stuck on the first setup step and the Next button does nothing. Had to reinstall."),
    _f("setup_stuck", "hi-en", "Pehle setup step pe atak gaya, Next button kaam hi nahi karta. Reinstall karna pada."),
    _f("unclear_plan_steps", "en", "I do not understand what the app wants me to do each day. No tutorial, no guide."),
    # ---------------- T06 ----------------
    _f("otp_not_received", "en", "OTP never arrives when I try to log in. I tried five times over {dn} days."),
    _f("otp_not_received", "hi-en", "Login ke time OTP aata hi nahi, {dn} din se try kar raha hu."),
    _f("crash_after_update", "en", "The app crashes on launch since the latest update. I cannot even open it.", ["uninstall"]),
    _f("crash_after_update", "hi-en", "Update ke baad app open karte hi crash ho jata hai."),
    _f("logged_out", "en", "I keep getting logged out and lose my food log for the day."),
    _f("logged_out", "hi-en", "Baar baar logout ho jata hu aur din ka food log gayab ho jata hai."),
    _f("slow_load", "en", "The home screen takes forever to load, sometimes over 30 seconds on good wifi."),
    # ---------------- T07 ----------------
    _f("coach_slow", "en", "I pay for a personal coach but replies take 2 to 3 days. For this price I expected daily check-ins.", ["cancel_intent"]),
    _f("coach_slow", "hi-en", "Coach ke liye paise diye par jawab 2-3 din mein aate hain. Is price mein roz ka follow-up expect tha."),
    _f("coach_generic", "en", "The coach just copy pastes the same generic diet chart. Nothing personal about it."),
    _f("coach_generic", "hi-en", "Coach har baar same generic diet chart bhej deta hai, personal kuch nahi."),
    _f("price_value", "en", "Premium costs Rs {amt} a year and honestly the free features of other apps do the same job.", ["competitor_mention"]),
    # ---------------- T08 ----------------
    _f("diabetic_plan", "en", "I am diabetic and the meal plan keeps suggesting high sugar foods. There is no way to set a medical condition."),
    _f("diabetic_plan", "hi-en", "Main diabetic hu par meal plan mein meethi cheezein hi suggest hoti hain."),
    _f("veg_plan", "en", "I told the app I am strictly vegetarian and it still suggests egg and chicken meals."),
    _f("veg_plan", "hi-en", "Main strictly vegetarian hu par plan mein baar baar egg aur chicken suggest karta hai."),
    _f("regional_plan", "en", "The diet plan has nothing for South Indian meals, it is all north Indian and western food."),
    _f("regional_plan", "hi-en", "Plan mein South Indian khana hai hi nahi, sab north Indian aur western hai."),
]

# Non-pain tickets: (category, lang, text). Slots {kg} {m}
NONPAIN = [
    ("praise", "en", "Love the app, lost {kg} kg in {m} months. The food diary is simple to use."),
    ("praise", "en", "Great app, the workout tracker keeps me motivated. Thank you team!"),
    ("praise", "en", "The coach was very helpful and friendly, really happy with my progress."),
    ("praise", "en", "Best fitness app I have used so far."),
    ("praise", "hi-en", "Bahut accha app hai, {m} mahine mein {kg} kg kam kiya. Thanks team!"),
    ("praise", "hi-en", "Coach ne bahut help ki, mast experience raha."),
    ("question", "en", "How do I change my registered email id?"),
    ("question", "en", "Can I use one subscription on two phones?"),
    ("question", "en", "Where can I download my progress report as a PDF?"),
    ("question", "hi-en", "Kya ek subscription do phone mein chal sakta hai?"),
    ("question", "hi-en", "Apna weight history export kaise karu?"),
    ("feature_request", "en", "Please add a water intake reminder widget."),
    ("feature_request", "en", "It would be great to have a dark mode."),
    ("feature_request", "en", "Please add support for logging yoga sessions with duration."),
    ("feature_request", "en", "Would love a weekly summary email with my progress."),
    ("feature_request", "hi-en", "Ek dark mode add kar do please."),
    ("feature_request", "hi-en", "Yoga session log karne ka option add karo."),
]

# Churn add-ons: flag -> lang -> texts. Slot {comp}
ADDONS = {
    "cancel_intent": {"en": ["Please cancel my subscription right away.", "I will not renew this plan."],
                      "hi-en": ["Mera subscription turant cancel kar do.", "Ab main ye plan renew nahi karunga."],
                      "hi": ["कृपया मेरा सब्सक्रिप्शन तुरंत बंद करें।"]},
    "uninstall": {"en": ["I have uninstalled the app.", "Uninstalling this now."],
                  "hi-en": ["Maine app uninstall kar diya hai."], "hi": ["मैंने ऐप हटा दिया है।"]},
    "competitor_mention": {"en": ["Thinking of switching to {comp}.", "{comp} does this much better."],
                           "hi-en": ["Ab {comp} pe shift hone ka soch raha hu.", "{comp} mein ye problem nahi hai."], "hi": []},
    "refund_dispute": {"en": ["I want my money back and will raise a dispute with my bank if needed."],
                       "hi-en": ["Paise wapas chahiye warna bank mein dispute karunga."], "hi": []},
}

OPENERS = {"en": ["Hi team,", "Hello support,", "To whom it may concern,", "Hi,", "", ""],
           "hi-en": ["Hi team,", "Hello,", "Namaste team,", "", ""], "hi": ["नमस्ते,", ""]}
CLOSERS = {"en": ["Please fix this soon.", "Kindly look into it.", "Waiting for your response.", "Thanks.", "", ""],
           "hi-en": ["Jaldi fix karo please.", "Please check karo.", "Reply ka wait hai.", "Thanks.", "", ""], "hi": ["धन्यवाद।", ""]}
DETAILS = {"en": ["This has been happening since last week.", "I have been a premium user for over a year.",
                  "I use an Android phone.", "This is the second time I am raising this.", "I updated the app yesterday."],
           "hi-en": ["Ye pichle hafte se ho raha hai.", "Main ek saal se premium user hu.", "Mere paas Android phone hai.",
                     "Ye doosri baar mail kar raha hu.", "Kal hi app update kiya tha."], "hi": []}
PRAISE_PREFIX = {"en": ["I really like the workout library. That said, ", "The app design is lovely and the coaches are nice. But "],
                 "hi-en": ["App ke workouts mast hain. Par "]}
JOIN = {"en": " Also, ", "hi-en": " Aur ek baat: ", "hi": " और एक बात: "}

FOODS = [("poha", 350, 180), ("paratha", 450, 250), ("chicken biryani", 650, 380), ("dal tadka", 320, 150),
         ("idli", 120, 40), ("masala dosa", 480, 250), ("paneer butter masala", 520, 320)]
HOME_DISHES = ["bhindi masala", "lauki kofta", "ragi mudde", "pesarattu", "thepla", "baingan bharta", "sambar rice"]
PLANS = ["Premium Monthly", "Premium Annual", "Premium Plus"]
DEVICES = ["Mi Band 6", "Fitbit Charge 5", "Noise ColorFit", "boAt Watch", "Galaxy Watch"]
COMPETITORS = ["cult.fit", "Fittr", "MyFitnessPal", "Strava"]
FIRST = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya", "Karthik", "Meera", "Rahul", "Divya", "Arjun", "Pooja",
         "Imran", "Nisha", "Suresh", "Kavya", "Amit", "Farah", "Deepak", "Lakshmi"]
LAST = ["Sharma", "Iyer", "Reddy", "Patel", "Nair", "Khan", "Gupta", "Menon", "Singh", "Das", "Joshi", "Rao"]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Kochi"]

EVENTS = [
    ("2026-08-18", "App release 8.4.0 (device sync rewrite)", "release", "T04 sync complaints and T06 crash/login complaints rise"),
    ("2026-09-15", "Hotfix 8.4.1 (sync fix)", "hotfix", "T04 returns to baseline within ~1 week"),
    ("2026-09-20", "Annual plan price change and new renewal flow", "pricing", "T01 and T02 volume rises and stays higher"),
]
