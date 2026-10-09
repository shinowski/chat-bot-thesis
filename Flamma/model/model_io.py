import json


class ModelIO:

    @staticmethod
    def save(network, filename):

        data = {
            "hidden": [],
            "output": []
        }

        for neuron in network.hidden.neurons:
            data["hidden"].append({
                "weights": neuron.weights,
                "bias": neuron.bias
            })

        for neuron in network.output.neurons:
            data["output"].append({
                "weights": neuron.weights,
                "bias": neuron.bias
            })

        with open(filename, "w") as file:
            json.dump(data, file, indent=4)


    @staticmethod
    def load(network, filename):

        with open(filename, "r") as file:
            data = json.load(file)

        # Hidden layer
        for neuron, saved in zip(
            network.hidden.neurons,
            data["hidden"]
        ):

            neuron.weights = saved["weights"]
            neuron.bias = saved["bias"]

        # Output layer
        for neuron, saved in zip(
            network.output.neurons,
            data["output"]
        ):

            neuron.weights = saved["weights"]
            neuron.bias = saved["bias"]