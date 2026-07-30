from model.dataset import Dataset

dataset = Dataset("data/intents.json")

texts, labels = dataset.prepare()

print("TEXTS")

for text in texts:
    print(text)

print()

print("LABELS")

for label in labels:
    print(label)