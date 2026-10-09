"""
test_cases.py
-------------
A held-out evaluation set for the 13 Flamma intents.

IMPORTANT: none of these sentences are copy-pasted verbatim from
intents.json. They're new paraphrases (plus a few deliberately messy
ones — typos, ambiguous phrasing, short fragments) so the evaluation
tells you something about generalization, not memorization.

Each entry is (text, expected_intent). Where a sentence is genuinely
ambiguous between two intents (the overlaps your earlier test run
surfaced), `expected_intent` is set to the ONE you decided is
operationally correct per the definitions:

    symptom   -> general skin complaint
    location  -> body location
    duration  -> time/history
    severity  -> intensity/progression

and a short note is added in the `notes` field explaining the
ambiguity, so a misclassification there is flagged as "known hard
case" rather than lumped in with plain errors.
"""

TEST_CASES = [
    # ---------------- greeting ----------------
    ("hey there, got a sec?", "greeting", None),
    ("morning! quick question about my skin", "greeting", None),
    ("is anyone able to help me rn", "greeting", None),
    ("hru", "greeting", "very short / slangy, stress test"),
    ("hiya can u help", "greeting", "typo-ish"),
    ("good afternoon, mind if i ask something", "greeting", None),

    # ---------------- symptom (general complaint) ----------------
    ("my skin is irritated", "symptom", None),
    ("i have red patches", "symptom", None),
    ("something's wrong with my skin", "symptom", None),
    ("i keep scratching my skin", "symptom", "known overlap w/ itching concept"),
    ("there are red patches on my skin", "symptom", "known overlap w/ rash appearance"),
    ("my skin feels weird lately", "symptom", None),
    ("i've got a bump that wont go away", "symptom", None),
    ("somthing is happening to my skin", "symptom", "typo"),

    # ---------------- location ----------------
    ("it's on my arm", "location", None),
    ("the rash is on my face", "location", None),
    ("i have it on my leg", "location", None),
    ("skin problem is on my arm", "location", "known hard case — model predicted symptom before"),
    ("mostly around my neck", "location", None),
    ("on both hands", "location", None),
    ("its my left elbow", "location", "typo, no apostrophe"),

    # ---------------- duration ----------------
    ("for two weeks", "duration", None),
    ("it started three days ago", "duration", None),
    ("i've had it for months", "duration", None),
    ("rash started two weeks ago", "duration", "known hard case — model predicted symptom before"),
    ("since last tuesday", "duration", None),
    ("about a year now", "duration", None),
    ("its been going on for a while, like 2 months", "duration", None),

    # ---------------- severity ----------------
    ("it hurts a lot", "severity", "known hard case — model predicted location before"),
    ("it's getting worse", "severity", None),
    ("it's unbearable", "severity", None),
    ("pretty mild honestly", "severity", None),
    ("the itching is really intense", "severity", "known overlap w/ itching concept"),
    ("i'd say 7 out of 10", "severity", None),
    ("its not that bad", "severity", None),

    # ---------------- confirmation ----------------
    ("nope", "confirmation", None),
    ("yeah", "confirmation", None),
    ("not really", "confirmation", None),
    ("i guess so", "confirmation", None),
    ("kinda", "confirmation", None),

    # ---------------- medication (asks + prior treatment) ----------------
    ("can i use a cream?", "medication", None),
    ("is it ok to put aloe vera on it", "medication", None),
    ("i already tried hydrocortisone", "medication", None),
    ("been using moisturizer but no change", "medication", None),
    ("should i take an antihistamine", "medication", None),
    ("what about benzoyl peroxide", "medication", None),

    # ---------------- emergency ----------------
    ("my face is swelling up fast and i can barely breathe", "emergency", None),
    ("the swelling is spreading to my throat", "emergency", None),
    ("i'm having trouble breathing and my lips are swollen", "emergency", None),
    ("chest feels tight and my skin is breaking out badly", "emergency", None),

    # ---------------- image_upload ----------------
    ("want me to send a pic", "image_upload", None),
    ("i can take a photo of it", "image_upload", None),
    ("here's an image of the rash", "image_upload", None),
    ("let me attach a picture", "image_upload", None),

    # ---------------- goodbye ----------------
    ("gotta go, bye", "goodbye", None),
    ("talk later", "goodbye", None),
    ("that's all for now, thanks bye", "goodbye", "overlap w/ thanks, but closes convo"),
    ("cya", "goodbye", None),

    # ---------------- thanks ----------------
    ("appreciate the help", "thanks", None),
    ("thanks so much", "thanks", None),
    ("that was useful, thank you", "thanks", None),
    ("ty", "thanks", "very short slang"),

    # ---------------- bot_identity ----------------
    ("are you a real doctor", "bot_identity", None),
    ("is this just an ai", "bot_identity", None),
    ("do you store what i tell you", "bot_identity", None),
    ("can you actually diagnose things", "bot_identity", None),

    # ---------------- unknown ----------------
    ("asdkfjalksdjf", "unknown", None),
    ("what does that even mean", "unknown", None),
    ("sorry ignore that", "unknown", None),
    ("random test message 123", "unknown", None),
]

if __name__ == "__main__":
    from collections import Counter
    counts = Counter(t[1] for t in TEST_CASES)
    print(f"Total test cases: {len(TEST_CASES)}")
    for intent, n in sorted(counts.items()):
        print(f"  {intent:14s} {n}")
