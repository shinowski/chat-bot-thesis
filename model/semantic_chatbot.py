from email.mime import message
import random
from model.knowledge_base import KnowledgeBase
from model.intent_classifier import IntentClassifier
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.dataset import Dataset


class SemanticChatbot:

    def receive_classification(self, classification, confidence):


        allowed_diseases = {
            "dermatitis",
            "lichen planus",
            "lichen_planus",
            "psoriasis",
            "rosacea",
        }

        if classification is None:
            return {
                "success": False,
                "message": "No classification result was provided."
            }

        normalized_classification = str(classification).lower().strip()

        if normalized_classification not in allowed_diseases:
            return {
                "success": False,
                "message": "The classification result is not supported by Flamma."
            }

        # Normalize Lichen Planus naming
        if normalized_classification == "lichen_planus":
            normalized_classification = "lichen planus"

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": "The classification confidence is invalid."
            }

        if confidence < 0.0 or confidence > 1.0:
            return {
                "success": False,
                "message": "The classification confidence must be between 0 and 1."
            }

        self.conversation.set(
            "classification",
            normalized_classification
        )

        self.conversation.set(
            "classification_confidence",
            confidence
        )

        self.conversation.set(
            "image_uploaded",
            True
        )

        return {
            "success": True,
            "classification": normalized_classification,
            "confidence": confidence
        }

    def __init__(self):
        # Load dataset for chatbot responses
        self.dataset = Dataset("data/intents.json")
        self.data = self.dataset.load()

        # Conversation memory
        self.conversation = Conversation()

        # Semantic intent classifier
        self.classifier = IntentClassifier()
        self.classifier.load("semantic_classifier.pkl")

        # Context and flow management
        self.context = ContextIntent()
        self.flow = FlowManager()
        self.knowledge = KnowledgeBase()

        print("Semantic chatbot initialized successfully!")

    def reply(self, message, image=None):

        # ==========================================================
        # IMAGE UPLOAD
        # ==========================================================

        if image is not None:
            print("\n========== IMAGE RECEIVED ==========")
            print("Filename:", image.filename)
            print("Content type:", image.content_type)
            print("====================================\n")

            self.conversation.set("image_uploaded", True)

            return {
                "reply": (
                    "Thanks! I've received the image. "
                    "I'm ready to analyze it."
                ),
                "intent": "image_upload",
                "confidence": 1.0,
                "followUps": []
            }

        # ==========================================================
        # 1. SEMANTIC INTENT PREDICTION
        # ==========================================================

        predicted_intent, confidence = self.classifier.predict(message)

        # ==========================================================
        # 2. GET EXPECTED CONVERSATION INTENT
        # ==========================================================

        expected_intent = self.flow.get_expected_intent(
            self.conversation
        )

        # ==========================================================
        # 3. RESOLVE INTENT USING CONTEXT
        # ==========================================================

        final_intent = self.context.resolve(
            predicted_intent,
            message,
            self.conversation,
            expected_intent
        )

            
        # ==========================================================
        # 4. HANDLE FINAL INTENT
        # ==========================================================

        if final_intent == "reset":

            self.conversation.reset()

            response = (
                "The screening has been restarted. "
                "Can you describe your skin problem?"
            )

        elif final_intent == "clarification":

            response = self.get_clarification_response(
                expected_intent
            )

        elif final_intent == "knowledge_question":

            response = self.get_knowledge_response(
                message,
                expected_intent
            )

        elif final_intent == "correction":

            response = self.handle_correction(
                message
            )

        elif final_intent == "invalid_location":

            response = (
                "I didn't understand the location. "
                "Please tell me where the affected area is, "
                "such as your arm, leg, face, or back."
            )

        elif final_intent == "invalid_duration":

            response = (
                "I didn't understand the duration. "
                "Please tell me how long you've had the problem, "
                "for example: two days, three weeks, or one month."
            )

        elif final_intent == "invalid_severity":

            response = (
                "I didn't understand the severity. "
                "Please answer with mild, moderate, or severe."
            )

        elif final_intent == "invalid_medication":

            response = (
                "I didn't understand the medication information. "
                "Please tell me whether you have used any medication, "
                "cream, ointment, or other treatment. "
                "You can also answer 'none' if you haven't used anything."
            )
        
        else:

            self.update_conversation(
                final_intent,
                message
            )

            screening_intents = {
                "symptom",
                "location",
                "duration",
                "severity",
                "medication",
            }

            if final_intent in screening_intents:

                response = self.get_screening_response(
                    final_intent
                )

            elif final_intent == "awaiting_image":

                response = (
                    "The screening information is complete. "
                    "Please upload a clear picture of the affected skin "
                    "to continue."
                )

            else:

                response = self.get_response(
                    final_intent
                )
                
        # ==========================================================
        # DEBUG INFORMATION
        # ==========================================================

        print("\n========== SEMANTIC CHATBOT ==========")
        print("User:", message)
        print("MiniLM prediction:", predicted_intent)
        print("MiniLM confidence:", round(float(confidence), 4))
        print("Expected intent:", expected_intent)
        print("Final intent:", final_intent)
        print("Conversation:", self.conversation.show())
        print("======================================\n")

        # ==========================================================
        # RETURN RESULT
        # ==========================================================

        return {
            "reply": response,
            "intent": str(final_intent),
            "confidence": float(confidence),
            "followUps": []
        }

    # ==============================================================
    # UPDATE CONVERSATION MEMORY
    # ==============================================================

    def update_conversation(self, intent, message):

        text = message.lower().strip()
        words = set(text.split())

        # ==========================================================
        # PRIMARY INTENT
        # ==========================================================

        if intent == "symptom":
            self.conversation.add_symptom(message)

        elif intent == "location":
            self.conversation.set(
                "location",
                message
            )

        elif intent == "duration":
            self.conversation.set(
                "duration",
                message
            )

        elif intent == "severity":
            self.conversation.set(
                "severity",
                message
            )

        if intent == "medication":

            text = message.lower().strip()

            no_medication_phrases = {
                "no",
                "none",
                "nothing",
                "nope",
                "not yet",
                "no medication",
                "no medicine",
                "i haven't",
                "i have not",
                "i didn't",
                "i did not",
                "i didnt",
                "i haven't used anything",
                "i have not used anything",
                "i didn't use anything",
                "i did not use anything",
                "i didnt use anything",
                "i didn't use",
                "i did not use",
                "i didnt use",
            }
            

            if (
                text in no_medication_phrases
                or "haven't used" in text
                or "have not used" in text
                or "didn't use" in text
                or "did not use" in text
            ):
                self.conversation.set(
                    "medication",
                    "none"
                )

            else:
                self.conversation.set(
                    "medication",
                    message
                )

        #elif intent == "image_upload":
        #    self.conversation.set(
        #        "image_uploaded",
        #        True
        #    )

        # ==========================================================
        # ADDITIONAL INFORMATION IN THE SAME MESSAGE
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

        # ==========================================================
        # STORE ADDITIONAL INFORMATION
        # ==========================================================

        # Don't overwrite a value with the entire message
        # when it was already saved as the primary intent.

        if has_location and intent != "location":
            self.conversation.set(
                "location",
                message
            )

        if has_duration and intent != "duration":
            self.conversation.set(
                "duration",
                message
            )

        if has_severity and intent != "severity":
            self.conversation.set(
                "severity",
                message
            )

    # ==============================================================
    # CLARIFICATION RESPONSES
    # ==============================================================

    def get_clarification_response(self, expected_intent):

        clarifications = {

            "symptom": (
                "I mean, what skin problem are you experiencing? "
                "For example, itching, redness, dryness, a rash, "
                "scaling, or another skin concern."
            ),

            "location": (
                "I mean, where on your body is the affected skin located? "
                "For example, your face, arm, leg, back, neck, or scalp."
            ),

            "duration": (
                "I mean, how long have you had this skin problem? "
                "For example, a few days, two weeks, or several months."
            ),

            "severity": (
                "I mean, how much is the skin problem bothering you? "
                "You can describe it as mild, moderate, or severe."
            ),

            "medication": (
                "I mean, have you applied or taken anything for the "
                "skin problem? For example, a cream, ointment, lotion, "
                "or medicine. You can also say none."
            ),

            "image_upload": (
                "I mean, please upload a clear photo of the affected "
                "skin so I can continue the screening."
            ),
        }

        return clarifications.get(
            expected_intent,
            (
                "Sure. Could you tell me which part "
                "you'd like me to explain?"
            )
        )

    # ==============================================================
    # NORMAL INTENT RESPONSE
    # ==============================================================

    def get_response(self, intent):

        for item in self.data["intents"]:

            if item["tag"] == intent:

                return random.choice(
                    item["responses"]
                )

        return "Sorry, I don't understand."


    def get_knowledge_response(self, message, expected_intent):

        parsed = self.knowledge.parse_question(message)

        disease = parsed["disease"]
        topic = parsed["topic"]

        # ----------------------------------------------------------
        # USE PREVIOUS KNOWLEDGE CONTEXT
        # ----------------------------------------------------------

        if disease is None:

            previous_disease = self.conversation.get(
                "knowledge_disease"
            )

            if previous_disease is not None:
                disease = previous_disease

        # ----------------------------------------------------------
        # DISEASE STILL UNKNOWN
        # ----------------------------------------------------------

        if disease is None:

            return (
                "I can provide information about Dermatitis, "
                "Lichen Planus, Psoriasis, and Rosacea. "
                "Which of these conditions would you like to know about?"
            )

        # ----------------------------------------------------------
        # REMEMBER CURRENT KNOWLEDGE DISEASE
        # ----------------------------------------------------------

        self.conversation.set(
            "knowledge_disease",
            disease
        )

        # ----------------------------------------------------------
        # RETRIEVE KNOWLEDGE
        # ----------------------------------------------------------

        knowledge = self.knowledge.get(
            disease,
            topic
        )

        if not knowledge:

            disease_name = self.knowledge.data[disease]["name"]

            answer = (
                f"I understand that you're asking about "
                f"{disease_name}, but I don't currently have "
                f"validated information for that topic."
            )

        else:

            answer = knowledge

        # ----------------------------------------------------------
        # RESUME UNFINISHED SCREENING
        # ----------------------------------------------------------

        if expected_intent is not None:

            next_question = self.flow.next_question(
                self.conversation
            )

            answer = (
                f"{answer}\n\n"
                f"To continue the screening: {next_question}"
            )

        return answer

    def get_screening_response(self, completed_intent):

        acknowledgements = {
            "symptom": "Thanks for describing what you're experiencing.",
            "location": "Got it. I've noted where the affected area is.",
            "duration": "Thanks. I've noted how long you've had it.",
            "severity": "Understood. I've noted the severity.",
            "medication": "Thanks. I've noted that information."
        }

        acknowledgement = acknowledgements.get(
            completed_intent,
            ""
        )

        next_question = self.flow.next_question(
            self.conversation
        )

        if acknowledgement:
            return f"{acknowledgement} {next_question}"

        return next_question

    def handle_correction(self, message):

        text = message.lower().strip()

        words = set(
            text.replace(",", "")
                .replace(".", "")
                .split()
        )

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
            "armpit",
            "knee", "knees",
            "elbow", "elbows",
            "lip", "lips",
        }

        duration_words = {
            "day", "days",
            "week", "weeks",
            "month", "months",
            "year", "years",
            "hour", "hours",
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
        }


        # ----------------------------------------------------------
        # LOCATION CORRECTION
        # ----------------------------------------------------------

        if any(
            word in words
            for word in location_words
        ):

            corrected_location = next(
                word
                for word in words
                if word in location_words
            )

            self.conversation.set(
                "location",
                corrected_location
            )

            next_question = self.flow.next_question(
                self.conversation
            )

            return (
                "No problem. I've updated the affected location. "
                f"{next_question}"
            )

        # ----------------------------------------------------------
        # DURATION CORRECTION
        # ----------------------------------------------------------

        if any(
            word in words
            for word in duration_words
        ):

            clean_text = (
                text.replace("sorry, i meant", "")
                    .replace("sorry i meant", "")
                    .replace("i meant", "")
                    .replace("actually", "")
                    .strip(" ,.")
            )

            self.conversation.set(
                "duration",
                clean_text
            )

            next_question = self.flow.next_question(
                self.conversation
            )

            return (
                "No problem. I've updated the duration. "
                f"{next_question}"
            )
        
        # ----------------------------------------------------------
        # SEVERITY CORRECTION
        # ----------------------------------------------------------

        if any(
            word in words
            for word in severity_words
        ):

            corrected_severity = next(
                word
                for word in words
                if word in severity_words
            )

            self.conversation.set(
                "severity",
                corrected_severity
            )

            next_question = self.flow.next_question(
                self.conversation
            )

            return (
                "No problem. I've updated the severity. "
                f"{next_question}"
            )
        # ----------------------------------------------------------
        # UNCLEAR CORRECTION
        # ----------------------------------------------------------

        return (
            "Sure. What would you like to correct — "
            "the affected location, duration, severity, "
            "or medication information?"
        )