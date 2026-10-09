from model.activation import Activation

print("Sigmoid")
print(Activation.sigmoid(-2))
print(Activation.sigmoid(0))
print(Activation.sigmoid(2))

print()

print("ReLU")
print(Activation.relu(-5))
print(Activation.relu(3))

print()

print("Softmax")
print(Activation.softmax([2, 5, 1]))