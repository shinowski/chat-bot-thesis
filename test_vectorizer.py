from model.vectorizer import Vectorizer

vectorizer = Vectorizer(max_length=10)

sentences = [

    [1,5,7,3],

    [2,8],

    [4,5,6,7,8,9]

]

vectors = vectorizer.transform(sentences)

for v in vectors:

    print(v)