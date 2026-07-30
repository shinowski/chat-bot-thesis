import math


class Activation:

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + math.exp(-x))


    @staticmethod
    def relu(x):
        return max(0, x)


    @staticmethod
    def relu_derivative(x):

        if x > 0:
            return 1

        return 0


    @staticmethod
    def softmax(values):

        exp_values = [math.exp(v) for v in values]

        total = sum(exp_values)

        return [v / total for v in exp_values]