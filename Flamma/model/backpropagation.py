class BackPropagation:

    @staticmethod
    def output_delta(predictions, targets):

        deltas = []

        for prediction, target in zip(predictions, targets):
            deltas.append(prediction - target)

        return deltas


    @staticmethod
    def weight_gradients(delta, inputs):

        gradients = []

        for input_value in inputs:
            gradients.append(delta * input_value)

        return gradients


    @staticmethod
    def bias_gradient(delta):

        return delta