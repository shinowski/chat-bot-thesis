from model.neuron import Neuron
from model.optimizer import SGD

neuron = Neuron(3)

print("Before")
print(neuron.weights)
print(neuron.bias)

optimizer = SGD(0.1)

optimizer.update_weights(
    neuron,
    [0.5, 0.2, -0.1]
)

optimizer.update_bias(
    neuron,
    0.3
)

print()

print("After")
print(neuron.weights)
print(neuron.bias)