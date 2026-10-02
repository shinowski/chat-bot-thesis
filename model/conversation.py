class Conversation:

    def __init__(self):

        self.reset()

    def reset(self):

        self.data = {
        "symptoms": [],
        "location": None,
        "duration": None,
        "severity": None,
        "medication": None,
        "image_uploaded": False,
        "classification": None,
        "classification_confidence": None,
        "knowledge_disease": None
    }

    def set(self, key, value):

        self.data[key] = value

    # New method
    def add_symptom(self, symptom):

        if symptom not in self.data["symptoms"]:
            self.data["symptoms"].append(symptom)

    def get(self, key):

        return self.data.get(key)

    def show(self):

        return self.data