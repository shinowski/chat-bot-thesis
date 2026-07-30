from model.gradients import Gradients

errors = [0.2, -0.3, 0.1]

hidden_outputs = [1.5, 0.8, 2.0]

gradients = Gradients.output_gradients(errors, hidden_outputs)

print("Gradients:")

for row in gradients:
    print(row)