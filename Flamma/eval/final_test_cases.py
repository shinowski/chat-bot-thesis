FINAL_TEST_CASES = [

    # =========================
    # GREETING — 10
    # =========================
    ("hello, can we talk for a moment?", "greeting"),
    ("good day, are you available?", "greeting"),
    ("hi, I have something to ask", "greeting"),
    ("hey there, can we chat?", "greeting"),
    ("morning, I need some assistance", "greeting"),
    ("hello there, could you assist me?", "greeting"),
    ("hi, is the assistant available?", "greeting"),
    ("hey, may I ask something?", "greeting"),
    ("good evening, can we talk?", "greeting"),
    ("hello, I could use some guidance", "greeting"),

    # =========================
    # SYMPTOM — 10
    # =========================
    ("my skin has become rough and irritated", "symptom"),
    ("I noticed several itchy spots on my skin", "symptom"),
    ("there are flaky areas appearing on my skin", "symptom"),
    ("I've developed some unusual red patches", "symptom"),
    ("my skin keeps itching and feels irritated", "symptom"),
    ("small raised spots appeared on my skin", "symptom"),
    ("I noticed dry patches that keep flaking", "symptom"),
    ("there is an irritated patch that keeps itching", "symptom"),
    ("my skin looks unusually red and scaly", "symptom"),
    ("I've noticed some new irritated areas", "symptom"),

    # =========================
    # LOCATION — 10
    # =========================
    ("the affected area is around my left elbow", "location"),
    ("I can see the irritation across my forehead", "location"),
    ("the spots are mostly around both knees", "location"),
    ("the affected skin is behind my neck", "location"),
    ("the irritated area is on my lower back", "location"),
    ("most of the patches are around my ankles", "location"),
    ("the skin issue appears near my right shoulder", "location"),
    ("the affected spots are along my upper chest", "location"),
    ("I can see the patches on both hands", "location"),
    ("the irritation is mainly around my scalp", "location"),

    # =========================
    # DURATION — 10
    # =========================
    ("this has been happening for nearly four days", "duration"),
    ("I first noticed it around three weeks back", "duration"),
    ("the skin issue has lasted roughly six months", "duration"),
    ("it appeared sometime earlier this week", "duration"),
    ("I've had the problem for around ten days", "duration"),
    ("this started approximately five weeks back", "duration"),
    ("the irritation has been present for several days", "duration"),
    ("I noticed it beginning about two months back", "duration"),
    ("it has stayed like this for almost a week", "duration"),
    ("the problem began sometime last month", "duration"),

    # =========================
    # SEVERITY — 10
    # =========================
    ("the discomfort is pretty minor", "severity"),
    ("I'd describe the irritation as fairly intense", "severity"),
    ("the itching has become extremely uncomfortable", "severity"),
    ("it's noticeable but still manageable", "severity"),
    ("the discomfort feels somewhere in the middle", "severity"),
    ("the irritation is not very strong", "severity"),
    ("it's becoming quite painful and difficult to ignore", "severity"),
    ("I'd say the symptoms are moderately uncomfortable", "severity"),
    ("the itching is very intense now", "severity"),
    ("the discomfort is mild enough to tolerate", "severity"),

    # =========================
    # CONFIRMATION — 10
    # =========================
    ("yes, that sounds correct", "confirmation"),
    ("that's what I was trying to say", "confirmation"),
    ("I believe that's correct", "confirmation"),
    ("yes, you've understood me correctly", "confirmation"),
    ("that seems about right", "confirmation"),
    ("no, that's not what I meant", "confirmation"),
    ("I don't think that's correct", "confirmation"),
    ("I'm not completely certain about that", "confirmation"),
    ("maybe, but I'm unsure", "confirmation"),
    ("that is mostly correct", "confirmation"),

    # =========================
    # MEDICATION — 10
    # =========================
    ("I've been applying a moisturizing cream to it", "medication"),
    ("I used an over-the-counter skin cream yesterday", "medication"),
    ("I haven't put any medicine on the area", "medication"),
    ("I've been taking an allergy tablet for the itching", "medication"),
    ("I applied some ointment to the irritated skin", "medication"),
    ("I haven't taken anything for the problem", "medication"),
    ("I've tried using a cream from the pharmacy", "medication"),
    ("I used a topical lotion on the affected area", "medication"),
    ("I haven't tried treating it with medicine", "medication"),
    ("I've already applied a skin ointment today", "medication"),

    # =========================
    # EMERGENCY — 10
    # =========================
    ("my throat is getting tighter and breathing is becoming difficult", "emergency"),
    ("I'm suddenly feeling faint while my face is swelling", "emergency"),
    ("the swelling around my mouth is increasing and I can't breathe normally", "emergency"),
    ("I'm struggling to stay conscious and a rash appeared suddenly", "emergency"),
    ("my tongue is getting bigger and swallowing is becoming difficult", "emergency"),
    ("I suddenly developed hives and now I'm having difficulty breathing", "emergency"),
    ("my skin reaction is spreading rapidly and I feel like I might faint", "emergency"),
    ("my lips are swelling quickly and my chest feels very tight", "emergency"),
    ("I have a very high fever and the skin reaction is worsening rapidly", "emergency"),
    ("the redness from the wound is rapidly streaking upward and I have a fever", "emergency"),

    # =========================
    # IMAGE_UPLOAD — 10
    # =========================
    ("I've attached a picture of the affected skin", "image_upload"),
    ("I just submitted a photo of the area", "image_upload"),
    ("here is an image showing the skin problem", "image_upload"),
    ("I've provided a picture for you to examine", "image_upload"),
    ("the photo of the affected area has been uploaded", "image_upload"),
    ("I sent an image showing what the patches look like", "image_upload"),
    ("I've included a photo of the irritation", "image_upload"),
    ("here's the picture I took of my skin", "image_upload"),
    ("I uploaded an image showing the affected spot", "image_upload"),
    ("the skin photo has been attached", "image_upload"),

    # =========================
    # GOODBYE — 10
    # =========================
    ("I need to head off, catch you later", "goodbye"),
    ("I'm going to leave now, bye", "goodbye"),
    ("that's everything for today, goodbye", "goodbye"),
    ("I'll be heading out now", "goodbye"),
    ("thanks, I'll talk to you later", "goodbye"),
    ("I'm finished for now, see you later", "goodbye"),
    ("I have to go now, goodbye", "goodbye"),
    ("that's all I needed, bye for now", "goodbye"),
    ("I'll come back another time", "goodbye"),
    ("I'm done chatting for today", "goodbye"),

    # =========================
    # THANKS — 10
    # =========================
    ("thank you for explaining that clearly", "thanks"),
    ("I really appreciate your assistance", "thanks"),
    ("thanks for taking the time to help", "thanks"),
    ("I appreciate the information you provided", "thanks"),
    ("many thanks for your guidance", "thanks"),
    ("that was useful, thank you", "thanks"),
    ("I appreciate you helping me understand", "thanks"),
    ("thank you, that cleared things up", "thanks"),
    ("thanks a lot for the explanation", "thanks"),
    ("I'm grateful for your help", "thanks"),

    # =========================
    # BOT_IDENTITY — 10
    # =========================
    ("what kind of assistant are you?", "bot_identity"),
    ("can you explain what Flamma does?", "bot_identity"),
    ("what is your role in this system?", "bot_identity"),
    ("are you an automated assistant?", "bot_identity"),
    ("what were you designed to help with?", "bot_identity"),
    ("tell me what this chatbot is for", "bot_identity"),
    ("what exactly can Flamma do?", "bot_identity"),
    ("are you the Flamma assistant?", "bot_identity"),
    ("what is the purpose of this chatbot?", "bot_identity"),
    ("can you tell me about yourself?", "bot_identity"),

    # =========================
    # UNKNOWN — 10
    # =========================
    ("what is the tallest mountain in Europe?", "unknown"),
    ("can you solve a quadratic equation for me?", "unknown"),
    ("who invented the telephone?", "unknown"),
    ("what ingredients do I need for pancakes?", "unknown"),
    ("how do I change my computer password?", "unknown"),
    ("tell me something about ancient Rome", "unknown"),
    ("what is the capital city of Canada?", "unknown"),
    ("can you recommend a movie to watch?", "unknown"),
    ("how many planets are in the solar system?", "unknown"),
    ("what does photosynthesis mean?", "unknown"),
]