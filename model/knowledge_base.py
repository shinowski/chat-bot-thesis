import json


class KnowledgeBase:

    def __init__(self, path="data/knowledge_base.json"):

        with open(path, "r", encoding="utf-8") as file:
            self.data = json.load(file)

    # ==========================================================
    # DETECT DISEASE
    # ==========================================================

    def detect_disease(self, message):

        text = message.lower()

        disease_aliases = {
            "dermatitis": "dermatitis",
            "lichen planus": "lichen_planus",
            "psoriasis": "psoriasis",
            "rosacea": "rosacea",
        }

        for phrase, disease_key in disease_aliases.items():
            if phrase in text:
                return disease_key

        return None

    # ==========================================================
    # DETECT KNOWLEDGE TOPIC
    # ==========================================================

    def detect_topic(self, message):

        text = message.lower()

        # Symptoms
        symptom_terms = (
            "symptom",
            "symptoms",
            "sign",
            "signs",
            "look like",
            "looks like",
        )

        if any(term in text for term in symptom_terms):
            return "symptoms"

        # Causes
        cause_terms = (
            "cause",
            "causes",
            "caused",
            "why do",
            "why does",
            "why is",
        )

        if any(term in text for term in cause_terms):
            return "causes"

        # Contagious
        contagious_terms = (
            "contagious",
            "infectious",
            "spread to",
            "catch it",
            "catch this",
        )

        if any(term in text for term in contagious_terms):
            return "contagious"

        # Management / treatment information
        management_terms = (
            "treatment",
            "treat",
            "treated",
            "manage",
            "management",
            "medicine",
            "medication",
            "cure",
            "cured",
        )

        if any(term in text for term in management_terms):
            return "management"

        # Referral
        referral_terms = (
            "doctor",
            "dermatologist",
            "hospital",
            "clinic",
            "professional",
            "specialist",
            "seek help",
            "medical help",
        )

        if any(term in text for term in referral_terms):
            return "referral"

        # General questions such as:
        # "What is psoriasis?"
        return "overview"

    # ==========================================================
    # GET KNOWLEDGE
    # ==========================================================

    def get(self, disease, topic):

        disease_data = self.data.get(disease)

        if disease_data is None:
            return None

        return disease_data.get(topic)

    # ==========================================================
    # PARSE QUESTION
    # ==========================================================

    def parse_question(self, message):

        disease = self.detect_disease(message)
        topic = self.detect_topic(message)

        return {
            "disease": disease,
            "topic": topic
        }