from model.pipeline import Pipeline

pipeline = Pipeline()

X, y = pipeline.prepare()

print("Input Vectors:\n")

for vector in X:
    print(vector)

print("\nLabels:\n")

print(y)