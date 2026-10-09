from model.dense import Dense

dense = Dense(3, 2)

inputs = [1.0, 2.0, 3.0]

dense.forward(inputs)

deltas = [-0.5, 0.2]

dense.backward(deltas)

for i, neuron in enumerate(dense.neurons):

    print(f"Neuron {i + 1}")

    print("Delta:")
    print(neuron.delta)

    print("Weight Gradients:")
    print(neuron.weight_gradients)

    print("Bias Gradient:")
    print(neuron.bias_gradient)

    print()