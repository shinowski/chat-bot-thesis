from model.neuron import Neuron

neuron = Neuron(3)

inputs = [1.0, 2.0, 3.0]

neuron.forward(inputs)

delta = -0.5

neuron.backward(delta)

print("Weights:")
print(neuron.weights)

print()

print("Inputs:")
print(neuron.inputs)

print()

print("Delta:")
print(neuron.delta)

print()

print("Weight Gradients:")
print(neuron.weight_gradients)

print()

print("Bias Gradient:")
print(neuron.bias_gradient)
