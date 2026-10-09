from model.text_understanding import has_screening_evidence


class Conversation:

    def __init__(self):

        self.reset()

    def reset(self):

        self.data = {
        "symptoms": [],
        "symptoms_unknown": False,
        "location": None,
        "duration": None,
        "severity": None,
        "medication": None,
        "image_uploaded": False,
        "classification": None,
        "classification_confidence": None,
        "image_condition": None,
        "knowledge_disease": None,
        "last_reply_intent": None,
        "pending_question": None,
        "last_knowledge_topics": [],
        "screening_paused": False,
        "last_image_status": None,
        "last_image_feedback": None,
        "invalid_answers": 0
    }

    def set(self, key, value):

        self.data[key] = value

    def restore(self, data):
        self.data.update(data)
        # Older versions could store low-confidence guesses such as "dssd"
        # as a location. Recheck those fields; the original chat is retained.
        for field in ['location', 'duration']:
            value = self.data.get(field)
            if value is not None and value != 'unknown' and (not isinstance(value, str) or not has_screening_evidence(field, value)):
                self.data[field] = None

    # New method
    def add_symptom(self, symptom):

        self.data["symptoms_unknown"] = False
        if symptom not in self.data["symptoms"]:
            self.data["symptoms"].append(symptom)

    def get(self, key):

        return self.data.get(key)

    def show(self):

        return self.data
