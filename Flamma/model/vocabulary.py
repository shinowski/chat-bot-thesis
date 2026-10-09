class Vocabulary:

    def __init__(self):

        self.word_to_index = {}

        self.index_to_word = {}

        self.next_index = 0


    def build(self, tokens):

        for token in tokens:

            if token not in self.word_to_index:

                self.word_to_index[token] = self.next_index

                self.index_to_word[self.next_index] = token

                self.next_index += 1


    def encode(self, tokens):

        encoded = []

        for token in tokens:

            encoded.append(self.word_to_index[token])

        return encoded
    
    def bag_of_words(self, tokens):

        vector = [0] * len(self.word_to_index)

        for token in tokens:

            if token in self.word_to_index:

                index = self.word_to_index[token]

                vector[index] = 1

        return vector