from model.dataset import Dataset
from model.tokenizer import Tokenizer
from model.vocabulary import Vocabulary
from model.label_encoder import LabelEncoder
from model.vectorizer import Vectorizer


class Pipeline:

    def __init__(self):

        self.dataset = Dataset("data/intents.json")
        self.tokenizer = Tokenizer()
        self.vocabulary = Vocabulary()
        self.label_encoder = LabelEncoder()
        self.vectorizer = Vectorizer(max_length=10)

    def prepare(self):

        texts, labels = self.dataset.prepare()

        tokenized = []

        for text in texts:

            tokens = self.tokenizer.tokenize(text)

            tokenized.append(tokens)

        # Build vocabulary

        for tokens in tokenized:

            self.vocabulary.build(tokens)

        encoded_sentences = []

        for tokens in tokenized:

            encoded = self.vocabulary.encode(tokens)

            encoded_sentences.append(encoded)

        vectors = self.vectorizer.transform(encoded_sentences)

        self.label_encoder.build(labels)

        encoded_labels = self.label_encoder.encode(labels)

        return vectors, encoded_labels