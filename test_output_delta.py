from model.backpropagation import BackPropagation

prediction = [
    0.15,
    0.75,
    0.10
]

target = [
    0,
    1,
    0
]

delta = BackPropagation.output_delta(
    prediction,
    target
)

print("Prediction:")
print(prediction)

print()

print("Target:")
print(target)

print()

print("Output Delta:")
print(delta)