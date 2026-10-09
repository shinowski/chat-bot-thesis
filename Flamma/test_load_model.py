from model.neural_network import NeuralNetwork
from model.model_io import ModelIO

network = NeuralNetwork(18, 8, 2)

ModelIO.load(network, "model_weights.json")

print("Model loaded successfully!")