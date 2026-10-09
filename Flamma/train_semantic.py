from model.intent_classifier import IntentClassifier


print("====================================")
print("   FLAMMA SEMANTIC MODEL TRAINING")
print("====================================")

classifier = IntentClassifier()

classifier.train()

classifier.save()

print("====================================")
print("   TRAINING COMPLETE")
print("====================================")
