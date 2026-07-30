class Vectorizer:

    def __init__(self, max_length=10):

        self.max_length = max_length


    def pad(self, encoded):

        vector = encoded[:self.max_length]

        while len(vector) < self.max_length:

            vector.append(0)

        return vector


    def transform(self, encoded_sentences):

        vectors = []

        for sentence in encoded_sentences:

            vectors.append(self.pad(sentence))

        return vectors