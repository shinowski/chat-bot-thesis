from model.tokenizer import Tokenizer
from model.vocabulary import Vocabulary

tokenizer = Tokenizer()
vocab = Vocabulary()

sentence = "Hello! My skin has been itchy for 3 days."

tokens = tokenizer.tokenize(sentence)

vocab.build(tokens)

print("Tokens:")
print(tokens)

print()

print("Vocabulary:")
print(vocab.word_to_index)

print()

print("Encoded:")
print(vocab.encode(tokens))