from model.tokenizer import Tokenizer

tokenizer = Tokenizer()

sentence = "Hello! My skin has been itchy for 3 days."

tokens = tokenizer.tokenize(sentence)

print(tokens)