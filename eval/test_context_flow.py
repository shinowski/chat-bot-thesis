from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager


context = ContextIntent()
flow = FlowManager()
conversation = Conversation()


tests = [
    ("my arm", "location"),
    ("the rash is on my face", "location"),
    ("skin problem is on my arm", "location"),
    ("for two weeks", "duration"),
    ("rash started two weeks ago", "duration"),
    ("it hurts a lot", "severity"),
    ("it's getting worse", "severity"),
    ("yeah", "confirmation"),
    ("nope", "confirmation"),
    ("cya", "goodbye"),
    ("ty", "thanks"),
]


print("====================================")
print("   CONTEXT + FLOW MANAGER TEST")
print("====================================")


for message, expected in tests:

    expected_intent = flow.get_expected_intent(conversation)

    # Simulate a bad MiniLM prediction.
    predicted_intent = "symptom"

    result = context.resolve(
        predicted_intent,
        message,
        conversation,
        expected_intent
    )

    print()
    print("Message:", message)
    print("Flow expected:", expected_intent)
    print("Model prediction:", predicted_intent)
    print("Final intent:", result)
    print("Expected:", expected)

    if result == expected:
        print("PASS")
    else:
        print("FAIL")


print()
print("====================================")
print("        TEST COMPLETE")
print("====================================")