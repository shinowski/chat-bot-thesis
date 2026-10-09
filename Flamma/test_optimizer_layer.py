from model.dense import Dense
from model.optimizer import SGD

layer = Dense(3, 2)

print("Before")

for neuron in layer.neurons:
    print(neuron.weights)
    print(neuron.bias)

# Fake gradients
for neuron in layer.neurons:
    neuron.weight_gradients = [0.1, 0.2, 0.3]
    neuron.bias_gradient = 0.5

optimizer = SGD(learning_rate=0.1)

optimizer.update_layer(layer)

print("\nAfter")

for neuron in layer.neurons:
    print(neuron.weights)
    print(neuron.bias)