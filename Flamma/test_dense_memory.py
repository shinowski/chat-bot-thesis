from model.dense import Dense

layer = Dense(4, 3)

sample = [1, 2, 3, 4]

output = layer.forward(sample)

print("Inputs:")
print(layer.inputs)

print()

print("Outputs:")
print(layer.outputs)