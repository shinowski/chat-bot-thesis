class Conversation:

    def __init__(self):

        self.reset()

    def reset(self):

        self.data = {
            "symptoms": [],          # Changed from "symptom": None
            "location": None,
            "duration": None,
            "severity": None,
            "medication": None,      # New field
            "image_uploaded": False
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