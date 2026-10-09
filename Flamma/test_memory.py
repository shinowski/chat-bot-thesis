from model.neuron import Neuron

neuron = Neuron(4)

sample = [1,2,3,4]

result = neuron.forward(sample)

print("Inputs:")
print(neuron.inputs)

print()

print("Output:")
print(neuron.output)

print()

print("Weights:")
print(neuron.weights)