from model.activation import Activation

print("ReLU Derivative Test")

print(Activation.relu_derivative(-5))
print(Activation.relu_derivative(0))
print(Activation.relu_derivative(8))