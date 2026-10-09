from model.text_understanding import (
    DURATION_WORDS, LOCATION_WORDS, MEDICATION_WORDS, PHOTO_WORDS, SYMPTOM_WORDS,
    clean_message, has_duration_answer, has_medication_answer, is_explicit_photo_request, is_photo_question, message_words,
)
from model.dialogue import dialogue_act, is_medication_report, looks_like_question as asks_question
from model.knowledge_base import KnowledgeBase, is_disease_overview_question, topic_requests


class ContextIntent:

    @staticmethod
    def normalize(message):
        return clean_message(message)

    @classmethod
    def is_image_followup(cls, message):
        return cls.normalize(message) in {
            "how about this", "what about this", "how about this one",
            "what about this one", "and this", "and this one",
        }

    @classmethod
    def is_image_request(cls, message):
        text = cls.normalize(message)
        words = message_words(text)
        mentions_photo = bool(words & {"picture", "pictures", "photo", "photos", "image", "images", "pic", "pics"})
        upload_action = bool(words & {"send", "upload", "attach", "share", "show", "submit", "sending", "uploading", "attaching"})
        if any(phrase in text for phrase in {"do not want to", "will not", "not going to", "cannot send", "cannot upload", "could not send", "could not upload"}):
            return False
        if is_photo_question(text) and not is_explicit_photo_request(text):
            return False
        return mentions_photo and upload_action

    @classmethod
    def is_declined_image_request(cls, message):
        text = cls.normalize(message)
        return bool(message_words(text) & {"picture", "pictures", "photo", "photos", "image", "images", "pic", "pics"}) and any(
            phrase in text for phrase in {"do not want to", "will not", "not going to", "cannot send", "cannot upload", "could not send", "could not upload"}
        )

    @classmethod
    def is_uncertain(cls, message):
        text = cls.normalize(message).replace("'", "")
        return text in {
            "i dont know", "i do not know", "dont know", "do not know",
            "im not sure", "i am not sure", "not sure", "unsure",
            "cant tell", "cannot tell", "i cant tell", "i cannot tell",
            "hard to tell", "i dont know how severe it is",
            "im not sure how severe it is", "i am not sure how severe it is",
            "i do not know how severe it is", "i have no idea", "no idea",
            "i am not sure yet", "i do not know yet", "skip",
        }

    def __init__(self, knowledge=None):
        self.knowledge = knowledge or KnowledgeBase()

    def resolve(
        self,
        predicted_intent,
        message,
        conversation,
        expected_intent=None
    ):
        text = self.normalize(message)
        words = message_words(text)

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

        if predicted_intent == "emergency" or any(phrase in text for phrase in emergency_phrases):
            return "emergency"

        if (
            ("breathing" in words or "breathe" in words)
            and ("swelling" in words or "swollen" in words)
        ):
            return "emergency"

        # ==========================================================
        # 2. CONVERSATION INTERRUPTIONS
        # ==========================================================
        # Photo requests and uncertainty can interrupt any screening question.
        # Only an actual accepted upload marks the image step complete.
        if self.is_image_request(message):
            return "image_request"

        if self.is_declined_image_request(message):
            return "image_declined"

        act = dialogue_act(message)
        named_disease = self.knowledge.detect_disease(message)
        if act is not None:
            if act == 'simple_explanation' and (topic_requests(message) or named_disease):
                return 'knowledge_question'
            if act == 'simple_explanation' and (conversation.get('classification') or conversation.get('last_image_status') == 'rejected') and text in {'what does it mean', 'what does that mean'} and not conversation.get('last_knowledge_topics'):
                return 'image_explanation'
            return act

        if self.is_uncertain(message):
            return "uncertain_answer"

        if self.is_image_followup(message) and conversation.get("image_uploaded"):
            return "image_followup"

        if is_disease_overview_question(message) or (named_disease and (asks_question(message) or text.removesuffix(' please') in self.knowledge.aliases)):
            return 'knowledge_question'

        photo_reference = words & (PHOTO_WORDS | {"result", "results", "heatmap"})
        another_topic = words & (MEDICATION_WORDS | {"psoriasis", "dermatitis", "rosacea", "lichen", "cause", "causes", "contagious", "doctor", "dermatologist"})
        has_photo_context = conversation.get("classification") or conversation.get("last_image_status") == "rejected"
        if has_photo_context and is_photo_question(message) and (photo_reference or not another_topic):
            return "image_explanation"

        topics = topic_requests(message)
        topic_fragment = bool(topics) and (
            len(words) <= 5 or text.startswith(('and ', 'what about ', 'how about '))
        ) and not words & (LOCATION_WORDS | DURATION_WORDS | SYMPTOM_WORDS | {'i', 'my', 'used', 'using', 'applied', 'tried', 'took', 'no', 'not', 'none', 'have'})
        if topics and (asks_question(message) or (topic_fragment and conversation.get('knowledge_disease'))):
            return "knowledge_question"


        # ----------------------------------------------------------
        # CORRECTION
        # ----------------------------------------------------------

        correction_phrases = {
            "i mean",
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
            "i do not understand",
            "i dont understand",
            "i don't get it",
            "i do not get it",
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

        disease_terms = self.knowledge.aliases
        if text.removesuffix(" please") in disease_terms:
            return "knowledge_question"

        knowledge_starters = (
            "what do ",
            "what would ",
            "tell me ",
            "explain ",
            "what is ",
            "what are ",
            "what causes ",
            "what cause ",
            "what does ",
            "why does ",
            "why do ",
            "how does ",
            "how do ",
            "how can ",
            "how to ",
            "can ",
            "is ",
            "are ",
            "should ",
            "will ",
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
            "medicine",
            "medication",
            "cream",
            "ointment",
        }

        mentions_disease = named_disease is not None

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
            message.rstrip().endswith("?")
            or text.startswith(knowledge_starters)
        )

        # A description followed by "can you help me?" is still a symptom
        # report, rather than a general question about a named disease.
        asks_for_help = any(phrase in text for phrase in {"can you help", "could you help", "help me"})
        describes_symptoms = bool(words & SYMPTOM_WORDS)

        help_with_symptoms = asks_for_help and describes_symptoms and not mentions_disease and not mentions_knowledge_topic
        if looks_like_question and (mentions_disease or mentions_knowledge_topic or references_previous_topic) and not help_with_symptoms:
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

        if expected_intent == "medication" and text in {"no", "nope", "none", "nothing", "not yet"}:
            return "medication"

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
            "that is all for now",
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
            "thanks a lot",
            "thanks so much",
            "thanks for your help",
            "thank you so much",
            "thank you very much",
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
            "hello there",
            "hey there",
            "hi there",
            "good morning",
            "good afternoon",
            "good evening",
        }

        greeting_phrases = {
            "how are you",
            "how r u",
            "how r you",
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

        if any(phrase in text for phrase in greeting_phrases) and not words & (SYMPTOM_WORDS | LOCATION_WORDS | DURATION_WORDS):
            return "greeting"

        # A treatment answer can mention a time or location without changing
        # the skin problem's duration/location question.
        if (expected_intent == "medication" and has_medication_answer(text)) or is_medication_report(message):
            return "medication"

        # ==========================================================
        # 6. INFORMATION SIGNAL DETECTION
        # ==========================================================

        location_words = LOCATION_WORDS

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

        has_duration = has_duration_answer(message)

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

        if describes_symptoms:
            return "symptom"

        # ----------------------------------------------------------
        # INVALID / UNKNOWN ANSWER VALIDATION
        # ----------------------------------------------------------

        words = message_words(text)

        # Validate location answers
        if expected_intent == "location":

            location_words = LOCATION_WORDS

            has_location = any(
                word in words
                for word in location_words
            )

            if not has_location:
                return "invalid_location"

        # Validate duration answers
        if expected_intent == "duration":

            has_duration = has_duration_answer(message)

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

        # Accepted treatment answers were handled before other field signals.
        if expected_intent == "medication":
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
