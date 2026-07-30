import json

class Dataset:

    def __init__(self, path):

        self.path = path

        self.data = None

        self.texts = []

        self.labels = []


    def load(self):

        with open(self.path, "r", encoding="utf-8") as file:

            self.data = json.load(file)

        return self.data


    def prepare(self):

        self.load()

        for intent in self.data["intents"]:

            tag = intent["tag"]

            for pattern in intent["patterns"]:

                self.texts.append(pattern)

                self.labels.append(tag)

        return self.texts, self.labels