from model.neuron import Neuron


class Dense:

    def __init__(self, input_size, output_size):

        self.neurons = []

        for _ in range(output_size):
            self.neurons.append(Neuron(input_size))

        self.inputs = None
        self.outputs = None


    def forward(self, inputs):

        self.inputs = inputs

        outputs = []

        for neuron in self.neurons:
            outputs.append(neuron.forward(inputs))

        self.outputs = outputs

        return outputs

    def get_neurons(self):

        return self.neurons

    def backward(self, deltas):

        previous_deltas = [0.0] * len(self.neurons[0].weights)

        for neuron, delta in zip(self.neurons, deltas):

            neuron.backward(delta)

            for i, weight in enumerate(neuron.weights):
                previous_deltas[i] += weight * delta

        return previous_deltas