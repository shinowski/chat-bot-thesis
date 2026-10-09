from model.neural_network import NeuralNetwork

# Same sizes used during training
input_size = 18
hidden_size = 8
output_size = 2

network = NeuralNetwork(
    input_size,
    hidden_size,
    output_size
)

# Example: "Hello"
sample = [
    1, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0
]

predicted_class, confidence = network.predict(sample)

print("Predicted Class:", predicted_class)
print("Confidence:", confidence)