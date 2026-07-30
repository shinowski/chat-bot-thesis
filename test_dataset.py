from model.dataset import Dataset

dataset = Dataset("data/intents.json")

data = dataset.load()

print(data)