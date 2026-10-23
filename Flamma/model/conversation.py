from model.text_understanding import has_screening_evidence


class Conversation:

    def __init__(self):

        self.reset()

    def reset(self):

        self.data = {
        "symptoms": [],
        "symptom_updates": [],
        "denied_symptoms": [],
        "symptoms_unknown": False,
        "location": None,
        "duration": None,
        "severity": None,
        "severity_discussion": None,
        "medication": None,
        "image_uploaded": False,
        "image_declined": False,
        "classification": None,
        "classification_confidence": None,
        "classification_image_id": None,
        "image_condition": None,
        "image_knowledge_key": None,
        "knowledge_disease": None,
        "knowledge_origin": None,
        "last_reply_intent": None,
        "pending_question": None,
        "last_knowledge_topics": [],
        "last_management_style": None,
        "pending_knowledge_choices": [],
        "pending_knowledge_topics": [],
        "pending_product_clarification": False,
        "mentioned_product": None,
        "pending_medication_report": None,
        "pending_screening_choices": None,
        "screening_paused": False,
        "last_image_status": None,
        "last_image_feedback": None,
        "invalid_answers": 0
    }

    def set(self, key, value):

        self.data[key] = value

    def invalidate_image_result(self, feedback):
        """Earlier photo results remain in history, never as the current result."""
        self.data.update(
            image_uploaded=False, classification=None, classification_confidence=None,
            classification_image_id=None,
            image_condition=None, image_knowledge_key=None, knowledge_disease=None, knowledge_origin=None, last_knowledge_topics=[], last_management_style=None,
            pending_knowledge_choices=[], pending_knowledge_topics=[], pending_product_clarification=False,
            pending_medication_report=None, pending_screening_choices=None,
            severity_discussion=None,
            last_image_status="rejected", last_image_feedback=feedback,
        )

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
