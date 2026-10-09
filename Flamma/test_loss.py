from model.loss import CrossEntropyLoss

loss = CrossEntropyLoss()

prediction = [0.1, 0.8, 0.1]

target = 1

print(loss.forward(prediction, target))