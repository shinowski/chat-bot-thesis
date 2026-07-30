import random
from model.conversation import Conversation
from model.dataset import Dataset
from model.tokenizer import Tokenizer
from model.vocabulary import Vocabulary
from model.label_encoder import LabelEncoder
from model.neural_network import NeuralNetwork
from model.model_io import ModelIO



class Chatbot:

    def __init__(self):

        # Load dataset
        self.dataset = Dataset("data/intents.json")
        self.data = self.dataset.load()
        self.conversation = Conversation()

        # Tokenizer
        self.tokenizer = Tokenizer()

        # Vocabulary
        self.vocabulary = Vocabulary()

        # Label encoder
        self.label_encoder = LabelEncoder()


        # Collect training data
        texts = []
        labels = []

        for intent in self.data["intents"]:

            tag = intent["tag"]

            for pattern in intent["patterns"]:

                texts.append(pattern)
                labels.append(tag)

        # Tokenize all texts
        tokenized_texts = []

        for text in texts:

            tokens = self.tokenizer.tokenize(text)

            tokenized_texts.append(tokens)

        # Build vocabulary
        for tokens in tokenized_texts:
            self.vocabulary.build(tokens)

        # Build label encoder
        self.label_encoder.build(labels)

        # Create neural network
        self.network = NeuralNetwork(
            input_size=len(self.vocabulary.word_to_index),
            hidden_size=8,
            output_size=len(self.label_encoder.label_to_index)
        )

        # Load trained weights
        ModelIO.load(self.network, "model_weights.json")

        print("Chatbot initialized successfully!")

    def reply(self, message):

        # Tokenize
        tokens = self.tokenizer.tokenize(message)

        # Bag of Words
        vector = self.vocabulary.bag_of_words(tokens)

        # Predict
        predicted_index, confidence = self.network.predict(vector)

        tag = self.label_encoder.decode(predicted_index)

        if tag == "symptom":
            self.conversation.add_symptom(message)

        elif tag == "location":
            self.conversation.set("location", message)

        elif tag == "duration":
            self.conversation.set("duration", message)

        elif tag == "severity":
            self.conversation.set("severity", message)

        # Find matching intent
        for intent in self.data["intents"]:

            print("\n========== MEMORY ==========")
            print(self.conversation.show())
            print("============================\n")

            if intent["tag"] == tag:

                import random

                return {
                    "reply": random.choice(intent["responses"]),
                    "intent": tag,
                    "confidence": confidence
                }

        return {
            "reply": "Sorry, I don't understand.",
            "intent": "unknown",
            "confidence": confidence
        }