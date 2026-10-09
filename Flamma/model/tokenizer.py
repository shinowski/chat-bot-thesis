import re

class Tokenizer:

    def tokenize(self, text):

        text = text.lower()

        tokens = re.findall(r"\b[a-z]+\b", text)

        return tokens