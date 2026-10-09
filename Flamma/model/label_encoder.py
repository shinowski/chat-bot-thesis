class LabelEncoder:

    def __init__(self):

        self.label_to_index = {}
        self.index_to_label = {}
        self.next_index = 0


    def build(self, labels):

        for label in labels:

            if label not in self.label_to_index:

                self.label_to_index[label] = self.next_index

                self.index_to_label[self.next_index] = label

                self.next_index += 1


    def encode(self, labels):

        encoded = []

        for label in labels:

            encoded.append(self.label_to_index[label])

        return encoded


    def decode(self, index):

        return self.index_to_label[index]