import math


class CrossEntropyLoss:

    def forward(self, prediction, target):

        epsilon = 1e-15

        prediction = max(prediction[target], epsilon)

        loss = -math.log(prediction)

        return loss