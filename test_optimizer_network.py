from model.neural_network import NeuralNetwork
from model.optimizer import SGD

network = NeuralNetwork(4, 5, 3)

print("Before")
print(network.output.neurons[0].weights)

# Fake gradients
for neuron in network.hidden.neurons:
    neuron.weight_gradients = [0.1] * len(neuron.weights)
    neuron.bias_gradient = 0.2

for neuron in network.output.neurons:
    neuron.weight_gradients = [0.1] * len(neuron.weights)
    neuron.bias_gradient = 0.2

optimizer = SGD(learning_rate=0.1)

optimizer.update_network(network)

print("\nAfter")
print(network.output.neurons[0].weights)
