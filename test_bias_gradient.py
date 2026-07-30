from model.backpropagation import BackPropagation

delta = -0.25

gradient = BackPropagation.bias_gradient(delta)

print("Delta:")
print(delta)

print()

print("Bias Gradient:")
print(gradient)
