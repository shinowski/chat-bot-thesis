from model.dataset import Dataset
from model.label_encoder import LabelEncoder

dataset = Dataset("data/intents.json")

texts, labels = dataset.prepare()

encoder = LabelEncoder()

encoder.build(labels)

print("Label Dictionary:")
print(encoder.label_to_index)

print()

encoded = encoder.encode(labels)

print("Encoded Labels:")
print(encoded)

print()

print("Decode Example:")
print(encoded[0], "->", encoder.decode(encoded[0]))