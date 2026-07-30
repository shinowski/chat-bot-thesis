from model.one_hot_encoder import OneHotEncoder

classes = [
    "greeting",
    "symptom",
    "medication"
]

encoder = OneHotEncoder(classes)

print(encoder.encode("greeting"))
print(encoder.encode("symptom"))
print(encoder.encode("medication"))
