from model.neural_network import NeuralNetwork

network = NeuralNetwork(
    input_size=4,
    hidden_size=5,
    output_size=3
)

inputs = [1.0, 2.0, 3.0, 4.0]

prediction = network.forward(inputs)

print("Prediction:")
print(prediction)

print()

output_deltas = [0.1, -0.2, 0.1]

network.backward(output_deltas)

print("Output Layer Gradients:")

for i, neuron in enumerate(network.output.neurons):

    print(f"\nNeuron {i+1}")

    print("Delta:", neuron.delta)

    print("Weight Gradients:", neuron.weight_gradients)

    print("Bias Gradient:", neuron.bias_gradient)
    