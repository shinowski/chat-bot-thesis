from model.context_intent import ContextIntent
from model.conversation import Conversation


context = ContextIntent()
conversation = Conversation()


tests = [
    ("yeah", "confirmation"),
    ("yes", "confirmation"),
    ("nope", "confirmation"),
    ("cya", "goodbye"),
    ("ty", "thanks"),
    ("my arm", "location"),
    ("the rash is on my face", "location"),
    ("skin problem is on my arm", "location"),
    ("for two weeks", "duration"),
    ("rash started two weeks ago", "duration"),
    ("it hurts a lot", "severity"),
    ("it's getting worse", "severity"),
]


print("====================================")
print("     CONTEXT INTENT TEST")
print("====================================")


for message, expected in tests:

    predicted_from_model = "symptom"

    result = context.resolve(
        predicted_from_model,
        message,
        conversation
    )

    print()
    print("Message:", message)
    print("Expected:", expected)
    print("Predicted:", result)

    if result == expected:
        print("PASS")
    else:
        print("FAIL")


print()
print("====================================")
print("        TEST COMPLETE")
print("====================================")
