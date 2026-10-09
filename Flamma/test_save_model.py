from model.neural_network import NeuralNetwork
from model.model_io import ModelIO

network = NeuralNetwork(18, 8, 2)

ModelIO.save(network, "model_weights.json")

print("Model saved successfully!")