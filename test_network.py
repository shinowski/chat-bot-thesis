from model.pipeline import Pipeline
from model.neural_network import NeuralNetwork

pipeline = Pipeline()

X, y = pipeline.prepare()

input_size = len(X[0])

output_size = len(set(y))

network = NeuralNetwork(
    input_size=input_size,
    hidden_size=8,
    output_size=output_size
)

prediction = network.forward(X[0])

print("Input:")
print(X[0])

print()

print("Prediction:")
print(prediction)