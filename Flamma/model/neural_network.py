from model.dense import Dense
from model.activation import Activation


class NeuralNetwork:

    def __init__(self, input_size, hidden_size, output_size):

        self.hidden = Dense(input_size, hidden_size)
        self.output = Dense(hidden_size, output_size)

    def forward(self, inputs):

        # Save input
        self.inputs = inputs

        # Hidden layer
        self.hidden_output = self.hidden.forward(inputs)

        # ReLU
        self.hidden_activation = [
            Activation.relu(x)
            for x in self.hidden_output
        ]

        # Save activated outputs inside each hidden neuron
        for i in range(len(self.hidden.neurons)):
            self.hidden.neurons[i].activated_output = self.hidden_activation[i]

        # Output layer
        self.output_raw = self.output.forward(self.hidden_activation)

        # Softmax
        self.output_prediction = Activation.softmax(self.output_raw)

        return self.output_prediction

    def backward(self, output_deltas):

        # Backpropagate through the output layer
        hidden_deltas = self.output.backward(output_deltas)

        # Apply ReLU derivative to hidden layer
        for i in range(len(hidden_deltas)):
            hidden_deltas[i] *= Activation.relu_derivative(
                self.hidden_output[i]
            )

        # Backpropagate through the hidden layer
        self.hidden.backward(hidden_deltas)

    def predict(self, inputs):

        prediction = self.forward(inputs)

        best_index = 0
        best_probability = prediction[0]

        for i in range(1, len(prediction)):

            if prediction[i] > best_probability:
                best_probability = prediction[i]
                best_index = i

        return best_index, best_probability