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

        # ----------------------------------------------------------
        # RESET / RESTART
        # ----------------------------------------------------------

        reset_phrases = {
            "reset",
            "restart",
            "start over",
            "start again",
            "new screening",
            "restart screening",
            "reset screening",
        }

        if text in reset_phrases:
            return "reset"

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
        

        # ----------------------------------------------------------
        # CORRECTION
        # ----------------------------------------------------------

        correction_phrases = {
            "i meant",
            "sorry i meant",
            "sorry, i meant",
            "actually",
            "correction",
            "let me correct that",
            "i need to correct that",
            "i want to correct that",
        }

        if any(
            phrase in text
            for phrase in correction_phrases
        ):
            return "correction"

        # ----------------------------------------------------------
        # CLARIFICATION
        # ----------------------------------------------------------

        clarification_words = {
            "what",
            "huh",
            "sorry",
            "pardon",
        }

        clarification_phrases = {
            "what do you mean",
            "what are you saying",
            "i don't understand",
            "i dont understand",
            "i don't get it",
            "i dont get it",
            "can you explain",
            "could you explain",
            "come again",
        }

        # Remove common ending punctuation so:
        # "what", "what?", and "what??" behave the same.
        clean_text = text.rstrip("?!.")

        if clean_text in clarification_words:
            return "clarification"

        if clean_text in clarification_phrases:
            return "clarification"

        # ----------------------------------------------------------
        # KNOWLEDGE QUESTION
        # ----------------------------------------------------------

        disease_terms = {
            "dermatitis",
            "lichen planus",
            "psoriasis",
            "rosacea",
        }

        knowledge_starters = (
            "what is ",
            "what are ",
            "what causes ",
            "what cause ",
            "what does ",
            "why does ",
            "why do ",
            "how does ",
            "how do ",
            "can ",
            "is ",
            "are ",
        )

        knowledge_topics = {
            "symptom",
            "symptoms",
            "cause",
            "causes",
            "contagious",
            "treatment",
            "treatments",
            "treated",
            "cure",
            "cured",
            "management",
            "manage",
        }

        mentions_disease = any(
            disease in text
            for disease in disease_terms
        )

        mentions_knowledge_topic = any(
            topic in words
            for topic in knowledge_topics
        )

        knowledge_reference_words = {
            "it",
            "this",
            "that",
            "condition",
            "disease",
        }

        references_previous_topic = any(
            word in words
            for word in knowledge_reference_words
        )

        looks_like_question = (
            text.endswith("?")
            or text.startswith(knowledge_starters)
        )

        if looks_like_question and (
        mentions_disease
        or mentions_knowledge_topic
        or references_previous_topic
        ):
         return "knowledge_question"

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
            "of course",
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

        # ----------------------------------------------------------
        # INVALID / UNKNOWN ANSWER VALIDATION
        # ----------------------------------------------------------

        words = set(
            text.replace(",", "")
                .replace(".", "")
                .replace("?", "")
                .replace("!", "")
                .split()
        )

        # Validate location answers
        if expected_intent == "location":

            location_words = {
                "arm", "arms",
                "leg", "legs",
                "face",
                "neck",
                "chest",
                "back",
                "hand", "hands",
                "foot", "feet",
                "scalp",
                "groin",
                "armpit", "armpits",
                "knee", "knees",
                "elbow", "elbows",
                "lip", "lips",
                "stomach",
                "abdomen",
                "shoulder", "shoulders",
            }

            has_location = any(
                word in words
                for word in location_words
            )

            if not has_location:
                return "invalid_location"

        # Validate duration answers
        if expected_intent == "duration":

            duration_words = {
                "hour", "hours",
                "day", "days",
                "week", "weeks",
                "month", "months",
                "year", "years",
                "today",
                "yesterday",
                "recently",
                "since",
                "ago",
            }

            has_duration = any(
                word in words
                for word in duration_words
            )

            if not has_duration:
                return "invalid_duration"

        # Validate severity answers
        if expected_intent == "severity":

            severity_words = {
                "mild",
                "moderate",
                "severe",
            }

            has_severity = any(
                word in words
                for word in severity_words
            )

            if not has_severity:
                return "invalid_severity"

        # Validate medication answers
        if expected_intent == "medication":

            no_medication_phrases = {
                "no",
                "none",
                "nothing",
                "nope",
                "not yet",
                "i haven't",
                "i have not",
                "haven't used anything",
                "i haven't used anything",
                "i have not used anything",
                "no medication",
                "no medicine",
            }

            medication_terms = {
                "cream",
                "ointment",
                "lotion",
                "medicine",
                "medication",
                "medications",
                "drug",
                "gel",
                "steroid",
                "hydrocortisone",
                "antihistamine",
                "antibiotic",
                "prescription",
                "tablet",
                "tablets",
                "pill",
                "pills",
            }

            is_no_medication = (
                text in no_medication_phrases
                or any(
                    phrase in text
                    for phrase in {
                        "haven't used",
                        "have not used",
                        "didn't use",
                        "did not use",
                        "not using",
                    }
                )
            )

            has_medication_term = any(
                word in words
                for word in medication_terms
            )

            if not is_no_medication and not has_medication_term:
                return "invalid_medication"

        # ---------------------------------------------------------
        # IMAGE UPLOAD MUST NOT BE INFERRED FROM TEXT
        # ----------------------------------------------------------

        if expected_intent == "image_upload":
            return "awaiting_image"

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