class ContextIntent:

    def __init__(self):
        pass

    def resolve(
        self,
        predicted_intent,
        message,
        conversation,
        expected_intent=None
    ):
        text = message.lower().strip()
        words = set(text.split())

        # ==========================================================
        # 1. EMERGENCY - HIGHEST PRIORITY
        # ==========================================================

        emergency_phrases = {
            "difficulty breathing",
            "trouble breathing",
            "having trouble breathing",
            "can't breathe",
            "cannot breathe",
            "barely breathe",
            "barely breathing",
            "chest feels tight",
            "chest is tight",
            "throat swelling",
            "swelling to my throat",
            "lips are swollen",
            "face is swelling",
        }

        emergency_words = {
            "breathing",
            "breathe",
            "swelling",
            "swollen",
        }

        if any(phrase in text for phrase in emergency_phrases):
            return "emergency"

        if (
            ("breathing" in words or "breathe" in words)
            and ("swelling" in words or "swollen" in words)
        ):
            return "emergency"

        # ==========================================================
        # 2. CONVERSATION INTERRUPTIONS
        # ==========================================================

        confirmation_words = {
            "yes",
            "yeah",
            "yep",
            "yup",
            "sure",
            "okay",
            "ok",
            "alright",
            "correct",
            "right",
            "exactly",
            "definitely",
            "of",
            "course",
            "no",
            "nope",
            "nah",
            "never",
            "kinda",
        }

        confirmation_phrases = {
            "not really",
            "i guess so",
            "i think so",
            "i suppose so",
            "sounds good",
            "that works",
            "i agree",
        }

        if text in confirmation_words:
            return "confirmation"

        if text in confirmation_phrases:
            return "confirmation"

        # ==========================================================
        # 3. GOODBYE
        # ==========================================================

        goodbye_words = {
            "bye",
            "goodbye",
            "see you",
            "see ya",
            "cya",
            "later",
            "take care",
        }

        goodbye_phrases = {
            "gotta go",
            "talk later",
            "see you later",
            "that's all for now",
        }

        if text in goodbye_words:
            return "goodbye"

        if any(phrase in text for phrase in goodbye_phrases):
            return "goodbye"

        # ==========================================================
        # 4. THANKS
        # ==========================================================

        thanks_words = {
            "thanks",
            "thank you",
            "thx",
            "ty",
            "thank u",
        }

        if text in thanks_words:
            return "thanks"

        # ==========================================================
        # 5. GREETING
        # ==========================================================

        greeting_words = {
            "hi",
            "hello",
            "hey",
            "hiya",
            "morning",
            "afternoon",
            "evening",
            "hru",
        }

        greeting_phrases = {
            "how are you",
            "how r u",
            "anyone there",
            "anyone here",
            "anyone able to help",
            "able to help me",
            "can you help",
            "could you help",
            "are you there",
            "got a sec",
            "got a minute",
            "quick question",
            "mind if i ask",
        }

        if text in greeting_words:
            return "greeting"

        if any(phrase in text for phrase in greeting_phrases):
            return "greeting"

        # ==========================================================
        # 6. INFORMATION SIGNAL DETECTION
        # ==========================================================

        location_words = {
            "arm",
            "arms",
            "leg",
            "legs",
            "face",
            "neck",
            "chest",
            "back",
            "hand",
            "hands",
            "foot",
            "feet",
            "scalp",
            "groin",
            "armpit",
            "knee",
            "knees",
            "elbow",
            "elbows",
            "lip",
            "lips",
        }

        duration_words = {
            "day",
            "days",
            "week",
            "weeks",
            "month",
            "months",
            "year",
            "years",
            "hour",
            "hours",
            "yesterday",
            "today",
            "ago",
            "since",
            "recently",
        }

        severity_words = {
            "mild",
            "moderate",
            "severe",
            "bad",
            "worse",
            "worst",
            "painful",
            "pain",
            "hurts",
            "hurt",
            "unbearable",
            "intense",
            "serious",
        }

        # ==========================================================
        # 7. MULTI-INFORMATION MESSAGES
        # ==========================================================

        has_location = any(
            word in words
            for word in location_words
        )

        has_duration = any(
            word in words
            for word in duration_words
        )

        has_severity = any(
            word in words
            for word in severity_words
        )

        # If the message contains multiple types of information,
        # use the current expected intent first.
        if expected_intent == "location" and has_location:
            return "location"

        if expected_intent == "duration" and has_duration:
            return "duration"

        if expected_intent == "severity" and has_severity:
            return "severity"

        # ==========================================================
        # 8. STRONG SINGLE INFORMATION SIGNALS
        # ==========================================================

        if has_location:
            return "location"

        if has_duration:
            return "duration"

        if has_severity:
            return "severity"

        # ==========================================================
        # 9. EXPECTED FLOW INTENT
        # ==========================================================

        if expected_intent is not None:
            if expected_intent in {
                "location",
                "duration",
                "severity",
                "medication",
                "image_upload",
            }:
                return expected_intent

        # ==========================================================
        # 10. FALL BACK TO MINILM
        # ==========================================================

        return predicted_intent