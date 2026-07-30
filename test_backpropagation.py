from model.backpropagation import Backpropagation

bp = Backpropagation()

prediction = [0.20, 0.70, 0.10]

target = 1

error = bp.output_error(prediction, target)

print("Prediction:")
print(prediction)

print()

print("Error:")
print(error)