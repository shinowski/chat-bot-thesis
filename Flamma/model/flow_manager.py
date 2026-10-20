class FlowManager:

    def get_expected_intent(self, conversation):
        data = conversation.show()
        if data.get("screening_paused"):
            return None

        if len(data["symptoms"]) == 0 and not data.get("symptoms_unknown"):
            return "symptom"

        if data["location"] is None:
            return "location"

        if data["duration"] is None:
            return "duration"

        if data["medication"] is None:
            return "medication"

        if not data["image_uploaded"] and not data.get('image_declined'):
            return "image_upload"

        return None

    def next_question(self, conversation):
        expected_intent = self.get_expected_intent(conversation)

        questions = {
            "symptom": "Can you describe your skin problem?",
            "location": "Where is the affected area located?",
            "duration": "How long have you had this problem?",
            "medication": "Have you applied any medication?",
            "image_upload": "For photo screening, you can upload a clear picture of the affected skin. You can also continue by text."
        }

        if expected_intent is None:
            if conversation.get("screening_paused"):
                return "Ask me about your skin concern or a photo result whenever you're ready."
            if conversation.get("image_uploaded"):
                return "You can ask about your photo result, discuss general care, or send another photo."
            if conversation.get('image_declined'):
                return "You can keep asking about skin concerns or name a condition for general information. These screening details alone do not identify a disease."
            return "Thank you. I have enough information for the next step."

        return questions[expected_intent]

    def follow_ups(self, conversation, expected_intent=None):
        options = {
            "location": ["My arm", "My face", "I'm not sure"],
            "duration": ["Two days", "Two weeks", "I'm not sure"],
            "medication": ["None", "I used a cream", "I'm not sure"],
            "image_upload": ["Text only", "Summarize our conversation"],
        }
        question = expected_intent if expected_intent is not None else self.get_expected_intent(conversation)
        return options.get(question, [])
