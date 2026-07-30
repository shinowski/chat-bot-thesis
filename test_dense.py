from model.dense import Dense

layer = Dense(input_size=10, output_size=5)

sample = [1,2,3,4,5,0,0,0,0,0]

output = layer.forward(sample)

print(output)