class OneHotEncoder:

    def __init__(self, classes):

        self.classes = classes


    def encode(self, label):

        vector = [0] * len(self.classes)

        index = self.classes.index(label)

        vector[index] = 1

        return vector