class FlowManager:

    def get_expected_intent(self, conversation):
        data = conversation.show()

        if len(data["symptoms"]) == 0:
            return "symptom"

        if data["location"] is None:
            return "location"

        if data["duration"] is None:
            return "duration"

        if data["severity"] is None:
            return "severity"

        if data["medication"] is None:
            return "medication"

        if not data["image_uploaded"]:
            return "image_upload"

        return None

    def next_question(self, conversation):
        expected_intent = self.get_expected_intent(conversation)

        questions = {
            "symptom": "Can you describe your skin problem?",
            "location": "Where is the affected area located?",
            "duration": "How long have you had this problem?",
            "severity": "How severe is it? Mild, moderate, or severe?",
            "medication": "Have you applied any medication?",
            "image_upload": "Please upload a clear picture of the affected skin."
        }

        if expected_intent is None:
            return "Thank you. I have enough information for the next step."

        return questions[expected_intent]