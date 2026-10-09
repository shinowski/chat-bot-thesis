from model.intent_classifier import IntentClassifier
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager
from eval.test_cases import TEST_CASES


print("====================================")
print(" FLAMMA CONTEXT-AWARE SEMANTIC TEST")
print("====================================")


# Load semantic model
classifier = IntentClassifier()
classifier.load("semantic_classifier.pkl")

# Initialize context components
context = ContextIntent()
flow = FlowManager()
conversation = Conversation()


correct = 0
total = len(TEST_CASES)

misclassifications = []


for message, expected, notes in TEST_CASES:

    # MiniLM prediction
    predicted_intent, confidence = classifier.predict(message)

    # Determine what the conversation currently expects
    expected_intent = flow.get_expected_intent(conversation)

    # Resolve using context
    final_intent = context.resolve(
        predicted_intent,
        message,
        conversation,
        expected_intent
    )

    if final_intent == expected:
        correct += 1
    else:
        misclassifications.append({
            "message": message,
            "expected": expected,
            "model_prediction": predicted_intent,
            "final_prediction": final_intent,
            "confidence": confidence,
            "notes": notes
        })


accuracy = correct / total * 100


print()
print("====================================")
print("RESULTS")
print("====================================")

print(f"Correct: {correct}/{total}")
print(f"Accuracy: {accuracy:.2f}%")


print()
print("====================================")
print("MISCLASSIFICATIONS")
print("====================================")


if len(misclassifications) == 0:

    print("No misclassifications!")

else:

    for item in misclassifications:

        print()
        print("Message:", item["message"])
        print("Expected:", item["expected"])
        print("MiniLM:", item["model_prediction"])
        print("Final:", item["final_prediction"])
        print("Confidence:", round(item["confidence"], 4))

        if item["notes"]:
            print("Notes:", item["notes"])


print()
print("====================================")
print("TEST COMPLETE")
print("====================================")