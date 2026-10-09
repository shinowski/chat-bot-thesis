from model.neuron import Neuron

neuron = Neuron(input_size=10)

sample = [1,2,3,4,5,0,0,0,0,0]

print("Weights:")
print(neuron.weights)

print()

print("Bias:")
print(neuron.bias)

print()

print("Output:")
print(neuron.forward(sample))