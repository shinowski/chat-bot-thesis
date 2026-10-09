import random


class Neuron:

    def __init__(self, input_size):

        self.weights = [
            random.uniform(-1, 1)
            for _ in range(input_size)
        ]

        self.bias = random.uniform(-1, 1)

        # Values remembered during forward pass
        self.inputs = []
        self.output = 0.0
        self.activated_output = 0.0

        # Gradients
        self.weight_gradients = [
            0.0 for _ in range(input_size)
        ]

        self.bias_gradient = 0.0

        # Error signal (delta)
        self.delta = 0.0


    def forward(self, inputs):

        self.inputs = inputs

        total = self.bias

        for input_value, weight in zip(inputs, self.weights):
            total += input_value * weight

        self.output = total

        return total


    def backward(self, delta):

        self.delta = delta

        self.bias_gradient = delta

        for i in range(len(self.weights)):
            self.weight_gradients[i] = delta * self.inputs[i]