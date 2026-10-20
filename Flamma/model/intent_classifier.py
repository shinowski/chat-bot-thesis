import pickle
from sklearn.linear_model import LogisticRegression

from model.semantic_model import SemanticModel
from model.text_understanding import normalize_message
from model.config import intent_model_path, read_intent_artifact
from model.training_data import load_training_examples


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
        examples, self.training_audit = load_training_examples()
        return [item['text'] for item in examples], [item['label'] for item in examples]

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

    def save(self, path=None):

        path = path if path is not None else intent_model_path()

        with open(path, "wb") as file:
            pickle.dump(self.classifier, file)

        print(f"Semantic classifier saved to {path}")

    def load(self, path=None):

        path = path if path is not None else intent_model_path()

        selected, artifact, checksum = read_intent_artifact(path)
        self.classifier = pickle.loads(artifact)
        self.model_path = selected
        self.model_sha256 = checksum

        self.labels = list(self.classifier.classes_)

        print(f"Semantic classifier loaded from {path}")
