import pickle
from sklearn.linear_model import LogisticRegression

from model.semantic_model import SemanticModel
from model.dataset import Dataset
from model.text_understanding import normalize_message


class IntentClassifier:

    def __init__(self):
        print("Initializing semantic intent classifier...")

        self.semantic_model = SemanticModel()

        self.classifier = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced"
    )

        self.labels = []

    def prepare_dataset(self):
        dataset = Dataset("data/intents.json")
        data = dataset.load()

        texts = []
        labels = []

        for intent in data["intents"]:
            tag = intent["tag"]

            for pattern in intent["patterns"]:
                texts.append(pattern)
                labels.append(tag)

        return texts, labels

    def train(self):

        print("Loading training data...")

        texts, labels = self.prepare_dataset()

        print(f"Training samples: {len(texts)}")
        print(f"Intent classes: {len(set(labels))}")

        print("Generating MiniLM embeddings...")

        embeddings = self.semantic_model.encode(texts)

        print(f"Embedding shape: {embeddings.shape}")

        print("Training Logistic Regression classifier...")

        self.classifier.fit(embeddings, labels)

        self.labels = list(self.classifier.classes_)

        print("Semantic classifier trained successfully!")

    def predict(self, text):

        embedding = self.semantic_model.encode([normalize_message(text)])

        prediction = self.classifier.predict(embedding)[0]

        probabilities = self.classifier.predict_proba(embedding)[0]

        confidence = max(probabilities)

        return prediction, confidence

    def save(self, path="semantic_classifier.pkl"):

        with open(path, "wb") as file:
            pickle.dump(self.classifier, file)

        print(f"Semantic classifier saved to {path}")

    def load(self, path="semantic_classifier.pkl"):

        with open(path, "rb") as file:
            self.classifier = pickle.load(file)

        self.labels = list(self.classifier.classes_)

        print(f"Semantic classifier loaded from {path}")
