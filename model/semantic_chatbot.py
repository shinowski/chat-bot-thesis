import random

from model.intent_classifier import IntentClassifier
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.dataset import Dataset


class SemanticChatbot:

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

        print("Semantic chatbot initialized successfully!")

    def reply(self, message, image=None):

                # --------------------------------
        # IMAGE UPLOAD
        # --------------------------------
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
                "confidence": 1.0
            }

        # 1. Predict intent using MiniLM + Logistic Regression
        predicted_intent, confidence = self.classifier.predict(message)

        # 2. Determine what information the conversation currently needs
        expected_intent = self.flow.get_expected_intent(
            self.conversation
        )

        # 3. Resolve intent using context + semantic prediction
        final_intent = self.context.resolve(
            predicted_intent,
            message,
            self.conversation,
            expected_intent
        )

        # 4. Update conversation memory
        self.update_conversation(
            final_intent,
            message
        )

        # 5. Find a response for the final intent
        response = self.get_response(final_intent)

        # Debug information
        print("\n========== SEMANTIC CHATBOT ==========")
        print("User:", message)
        print("MiniLM prediction:", predicted_intent)
        print("MiniLM confidence:", round(confidence, 4))
        print("Expected intent:", expected_intent)
        print("Final intent:", final_intent)
        print("Conversation:", self.conversation.show())
        print("======================================\n")

        return {
                "reply": response,
                "intent": final_intent,
                "confidence": float(confidence),
                "followUps": []
            }

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

        elif intent == "medication":
            self.conversation.set(
                "medication",
                message
            )

        elif intent == "image_upload":
            self.conversation.set(
                "image_uploaded",
                True
            )

        # ==========================================================
        # ADDITIONAL INFORMATION IN THE SAME MESSAGE
        # ==========================================================

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

    def get_response(self, intent):

        for item in self.data["intents"]:

            if item["tag"] == intent:

                return random.choice(
                    item["responses"]
                )

        return "Sorry, I don't understand."
