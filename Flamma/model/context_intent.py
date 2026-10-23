import re

from model.text_understanding import (
    DURATION_WORDS, LOCATION_WORDS, MEDICATION_WORDS, PHOTO_WORDS, PHOTO_REFERENCES, SYMPTOM_WORDS, SEVERITY_WORDS,
    clean_message, has_duration_answer, has_medication_answer, is_explicit_photo_request, is_photo_question, message_words, symptom_mentions, no_medication,
)
from model.dialogue import dialogue_act, is_medication_report, medication_use_reference, looks_like_question as asks_question
from model.knowledge_base import KnowledgeBase, is_disease_overview_question, is_diagnosis_question, topic_requests, is_course_question
from model.safety import is_care_question, safety_intent
from model.chat_support import unrelated_request, support_intent, emotional_only
from model.question_clarification import clarification_request, bare_product_answer, knowledge_choice_index, screening_choice_answer, explicit_fact_replacement
from model.conversation_language import uncertainty_detail, is_symptom_update
from model.severity_support import discussion_route


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
        if uncertainty_detail(message)[0]:
            return True
        text = cls.normalize(message).replace("'", "")
        return text in {
            "i dont know", "i do not know", "dont know", "do not know",
            "im not sure", "i am not sure", "not sure", "unsure",
            "cant tell", "cannot tell", "i cant tell", "i cannot tell",
            "hard to tell", "i dont know how severe it is",
            "im not sure how severe it is", "i am not sure how severe it is",
            "i do not know how severe it is", "i have no idea", "no idea",
            "i am not sure yet", "i do not know yet", "skip",
        } or bool(re.fullmatch(
            r'(?:i (?:do not|cannot) (?:know|remember|recall)|i forgot|i am not sure|not sure) '
            r'(?:what i (?:used|applied|took)|which (?:cream|medicine|medication|ointment|product) (?:i (?:used|applied|took)|it was)|'
            r'(?:its|the|that|the products|the medicines) name)', text
        ))

    @classmethod
    def uncertain_target(cls, message):
        detail = uncertainty_detail(message)
        if detail[0]:
            return detail[1]
        text = cls.normalize(message)
        if cls.is_uncertain(message) and re.search(r'\b(?:what i (?:used|applied|took)|which (?:cream|medicine|medication|ointment|product) i (?:used|applied|took))\b', text):
            return 'medication'
        return None

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

        safety = safety_intent(message)
        if safety:
            return safety
        if emotional_only(message):
            return 'emotional_support'
        if is_care_question(message):
            return 'knowledge_question'
        if unrelated_request(message):
            return 'out_of_scope'
        support = support_intent(message)
        if support:
            return support

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
        if act is None and len(self.knowledge.detect_diseases(message)) <= 1 and discussion_route(message, conversation):
            return 'severity_guidance'
        if act is not None:
            if act == 'simple_explanation' and (topic_requests(message) or named_disease):
                return 'knowledge_question'
            if act == 'simple_explanation' and (conversation.get('classification') or conversation.get('last_image_status') == 'rejected') and text in {'what does it mean', 'what does that mean'} and not conversation.get('last_knowledge_topics'):
                return 'image_explanation'
            return act

        if is_course_question(message):
            return 'knowledge_question'
        if self.is_uncertain(message):
            return "uncertain_answer"
        if is_symptom_update(message, conversation.get('mentioned_product')):
            return 'symptom_update'

        choices = conversation.get('pending_screening_choices')
        if screening_choice_answer(message, choices) is not None:
            return choices['field']
        if choices and knowledge_choice_index(message) is not None:
            return choices['field'] + '_clarification'
        if explicit_fact_replacement(message):
            return 'correction'

        clarification = clarification_request(message, self.knowledge)
        if clarification:
            if clarification[0] == 'product_clarification' and conversation.get('mentioned_product') and re.fullmatch(
                r'(?:can|should|could|may) i (?:use|apply|take|try) (?:it|that|this)(?: (?:on|for|to) .+)?', text
            ):
                return 'product_information'
            return clarification[0]
        if is_diagnosis_question(message, bool(named_disease)):
            return 'diagnosis_question'
        if conversation.get('pending_knowledge_choices') and not named_disease and (topic_requests(message) or is_disease_overview_question(message)):
            return 'condition_clarification'
        choice = knowledge_choice_index(message)
        if conversation.get('pending_knowledge_choices') and choice is not None:
            return 'knowledge_question' if choice < len(conversation.get('pending_knowledge_choices')) else 'condition_clarification'
        if conversation.get('pending_product_clarification') and not named_disease and bare_product_answer(message) and not message_words(message) & (SYMPTOM_WORDS | LOCATION_WORDS | DURATION_WORDS):
            if text not in {'hi', 'hello', 'hey', 'thanks', 'thank you', 'bye', 'yes', 'no'}:
                return 'product_information'

        if conversation.get('pending_medication_report') and not named_disease and bare_product_answer(message) and not words & (SYMPTOM_WORDS | LOCATION_WORDS | DURATION_WORDS):
            return 'medication'
        if medication_use_reference(message) and not conversation.get('mentioned_product') and not words & MEDICATION_WORDS and not asks_question(message):
            return 'medication' if no_medication(message) else 'medication_clarification'

        if self.is_image_followup(message) and conversation.get("image_uploaded"):
            return "image_followup"

        if self.knowledge.is_condition_followup(message) or is_disease_overview_question(message) or (named_disease and (asks_question(message) or text.removesuffix(' please') in self.knowledge.aliases or re.search(r'\bi (?:think|suspect|have|was told|was diagnosed)\b|\b(?:doctor|dermatologist|clinician) (?:diagnosed|said|suspects)\b', text))):
            return 'knowledge_question'

        photo_reference = words & PHOTO_REFERENCES
        topics = topic_requests(message)
        if photo_reference and topics:
            return 'knowledge_question'
        another_topic = words & (MEDICATION_WORDS | {"psoriasis", "dermatitis", "rosacea", "lichen", "cause", "causes", "contagious", "doctor", "dermatologist"})
        has_photo_context = conversation.get("classification") or conversation.get("last_image_status") == "rejected"
        if has_photo_context and is_photo_question(message) and (photo_reference or not another_topic):
            return "image_explanation"

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
        affirmative_symptoms, denied_symptoms = symptom_mentions(message)
        describes_symptoms = bool(affirmative_symptoms)

        help_with_symptoms = asks_for_help and describes_symptoms and not mentions_disease and not mentions_knowledge_topic
        if looks_like_question and (mentions_disease or mentions_knowledge_topic or references_previous_topic) and not help_with_symptoms:
            return "knowledge_question"

        if is_medication_report(message, conversation.get('mentioned_product')) or (expected_intent == 'medication' and has_medication_answer(message)):
            return 'medication'

        if denied_symptoms and not affirmative_symptoms:
            return 'symptom_denial'

        # Recognized questions and conversation acts take priority over a guess.
        # Unfamiliar warning wording still gets a conditional safety check.
        safety = safety_intent(message, predicted_intent)
        if safety:
            return safety

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

        # ==========================================================
        # 6. INFORMATION SIGNAL DETECTION
        # ==========================================================

        location_words = LOCATION_WORDS

        severity_words = SEVERITY_WORDS

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

            severity_words = SEVERITY_WORDS

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
