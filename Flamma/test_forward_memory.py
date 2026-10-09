from model.pipeline import Pipeline
from model.neural_network import NeuralNetwork

pipeline = Pipeline()

X, y = pipeline.prepare()

network = NeuralNetwork(
    input_size=len(X[0]),
    hidden_size=8,
    output_size=len(set(y))
)

prediction = network.forward(X[0])

print("Input:")
print(network.inputs)

print()

print("Hidden Output:")
print(network.hidden_output)

print()

print("Hidden Activation:")
print(network.hidden_activation)

print()

print("Output Raw:")
print(network.output_raw)

print()

print("Prediction:")
print(network.output_prediction)