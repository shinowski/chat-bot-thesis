class FlowManager:

    def next_question(self, conversation):

        data = conversation.show()

        # Need symptom first
        if len(data["symptoms"]) == 0:
            return "Can you describe your skin problem?"

        # Need location
        if data["location"] is None:
            return "Where is the affected area located?"

        # Need duration
        if data["duration"] is None:
            return "How long have you had this problem?"

        # Need severity
        if data["severity"] is None:
            return "How severe is it? Mild, moderate, or severe?"

        # Need medication history
        if data["medication"] is None:
            return "Have you applied any medication?"

        # Ready for image
        if not data["image_uploaded"]:
            return "Please upload a clear picture of the affected skin."

        return "Thank you. I have enough information for the next step."