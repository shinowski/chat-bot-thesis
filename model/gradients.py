class Gradients:

    @staticmethod
    def output_gradients(errors, hidden_outputs):

        gradients = []

        for error in errors:

            neuron_gradients = []

            for value in hidden_outputs:

                neuron_gradients.append(error * value)

            gradients.append(neuron_gradients)

        return gradients