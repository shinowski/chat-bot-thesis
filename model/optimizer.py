class SGD:

    def __init__(self, learning_rate=0.01):

        self.learning_rate = learning_rate


    def update_neuron(self, neuron):

        # Update each weight
        for i in range(len(neuron.weights)):
            neuron.weights[i] -= (
                self.learning_rate *
                neuron.weight_gradients[i]
            )

        # Update bias
        neuron.bias -= (
            self.learning_rate *
            neuron.bias_gradient


        )


    def update_layer(self, layer):

        for neuron in layer.neurons:
            self.update_neuron(neuron)

    def update_network(self, network):

        self.update_layer(network.hidden)

        self.update_layer(network.output)