from model.dataset import Dataset
from model.tokenizer import Tokenizer
from model.vocabulary import Vocabulary
from model.label_encoder import LabelEncoder
from model.neural_network import NeuralNetwork
from model.loss import CrossEntropyLoss
from model.optimizer import SGD
from model.backpropagation import BackPropagation
from model.model_io import ModelIO


class Trainer:

    def __init__(self):

        self.dataset = Dataset("data/intents.json")
        self.tokenizer = Tokenizer()
        self.vocabulary = Vocabulary()
        self.label_encoder = LabelEncoder()
        self.loss = CrossEntropyLoss()
        self.optimizer = SGD(learning_rate=0.01)

    def train(self, epochs=100):

        data = self.dataset.load()

        texts = []
        labels = []

        for intent in data["intents"]:

            tag = intent["tag"]

            for pattern in intent["patterns"]:

                texts.append(pattern)
                labels.append(tag)

        print("TEXTS")

        for text in texts:
            print(text)

        print("\nLABELS")

        for label in labels:
            print(label)
        
        # Tokenize all texts
        tokenized_texts = []

        for text in texts:

            tokens = self.tokenizer.tokenize(text)

            tokenized_texts.append(tokens)

            print("\nTOKENIZED")

        for tokens in tokenized_texts:
            print(tokens)
        
        # Build vocabulary
        for tokens in tokenized_texts:
            self.vocabulary.build(tokens)

            print("\nVOCABULARY")
            print(self.vocabulary.word_to_index)
        
        # Encode every sentence
        encoded_texts = []

        for tokens in tokenized_texts:

            encoded = self.vocabulary.encode(tokens)

            encoded_texts.append(encoded)

            print("\nENCODED TEXTS")

        for encoded in encoded_texts:
            print(encoded)

        # Build label encoder
        self.label_encoder.build(labels)

        print("\nLABEL MAPPING")
        print(self.label_encoder.label_to_index)

        # Encode labels
        encoded_labels = self.label_encoder.encode(labels)

        print("\nENCODED LABELS")

        print(encoded_labels)

        # Convert to Bag-of-Words vectors
        bow_vectors = []

        for tokens in tokenized_texts:

            vector = self.vocabulary.bag_of_words(tokens)

            bow_vectors.append(vector)

        print("\nBAG OF WORDS")

        for vector in bow_vectors:
            print(vector)

        # Create the neural network
        input_size = len(self.vocabulary.word_to_index)
        hidden_size = 8
        output_size = len(self.label_encoder.label_to_index)

        self.network = NeuralNetwork(
            input_size,
            hidden_size,
            output_size
        )

        print("\nNETWORK CREATED")
        print("Input Size:", input_size)
        print("Hidden Size:", hidden_size)
        print("Output Size:", output_size)

        print("\n================ TRAINING ================\n")

        for epoch in range(epochs):

            total_loss = 0

            for sample, target in zip(bow_vectors, encoded_labels):

                prediction = self.network.forward(sample)

                loss = self.loss.forward(prediction, target)
                total_loss += loss

                target_vector = [0] * output_size
                target_vector[target] = 1

                output_deltas = BackPropagation.output_delta(
                    prediction,
                    target_vector
                )

                self.network.backward(output_deltas)

                self.optimizer.update_network(self.network)

            print(
                f"Epoch {epoch + 1}/{epochs} | Loss: {total_loss:.4f}"
            )

        ModelIO.save(
            self.network,
            "model_weights.json"
        )

        print(
                f"Epoch {epoch + 1}/{epochs} | Loss: {total_loss:.4f}"
            )

        # ==========================
        # TRAINING ACCURACY
        # ==========================

        print("\n============= TRAINING ACCURACY =============")

        correct = 0

        for sample, target in zip(bow_vectors, encoded_labels):

            predicted_class, confidence = self.network.predict(sample)

            if predicted_class == target:
                correct += 1

        accuracy = correct / len(bow_vectors) * 100

        print(f"Accuracy: {accuracy:.2f}%")

        # ==========================
        # SAVE MODEL
        # ==========================

        ModelIO.save(
            self.network,
            "model_weights.json"
        )

        print("\n============= TRAINING COMPLETE =============")
        print("Model saved successfully!")

