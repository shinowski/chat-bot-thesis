from model.backpropagation import BackPropagation

delta = -0.25

inputs = [
    1.2,
    0.5,
    0.8
]

gradients = BackPropagation.weight_gradients(
    delta,
    inputs
)

print("Delta:")
print(delta)

print()

print("Inputs:")
print(inputs)

print()

print("Weight Gradients:")
print(gradients)
