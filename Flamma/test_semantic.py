from model.intent_classifier import IntentClassifier


print("====================================")
print("     FLAMMA SEMANTIC MODEL TEST")
print("====================================")

classifier = IntentClassifier()

classifier.load("semantic_classifier.pkl")


test_messages = [
    "Hello",
    "My skin is very itchy",
    "I keep scratching my skin",
    "There are red patches on my skin",
    "The rash started two weeks ago",
    "It is getting worse",
    "It hurts a lot",
    "Can I use a cream for this?",
    "My skin problem is on my arm",
    "Goodbye"
]


for message in test_messages:

    intent, confidence = classifier.predict(message)

    print("\nMessage:", message)
    print("Intent:", intent)
    print("Confidence:", round(confidence, 4))


print("\n====================================")
print("        TEST COMPLETE")
print("====================================")
