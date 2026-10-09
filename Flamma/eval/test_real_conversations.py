from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.context_intent import ContextIntent


def run_conversation(name, messages, expected_intents):
    print("\n====================================")
    print(name)
    print("====================================")

    conversation = Conversation()
    flow_manager = FlowManager()
    context_intent = ContextIntent()

    passed = True

    for i, (message, expected) in enumerate(
        zip(messages, expected_intents), start=1
    ):

        # Determine what the flow expects BEFORE processing the message
        expected_flow_intent = flow_manager.get_expected_intent(
            conversation
        )

        # For this test, we use the message itself with a simple
        # placeholder predicted intent.
        predicted_intent = expected_flow_intent or "unknown"

        final_intent = context_intent.resolve(
            predicted_intent=predicted_intent,
            message=message,
            conversation=conversation,
            expected_intent=expected_flow_intent
        )

        print(f"\nTurn {i}")
        print(f"User:     {message}")
        print(f"Expected: {expected}")
        print(f"Final:    {final_intent}")

        if final_intent == expected:
            print("PASS")
        else:
            print("FAIL")
            passed = False

        # Update conversation state based on the recognized intent
        update_conversation(
            conversation,
            final_intent,
            message
        )

    print("\n------------------------------------")

    if passed:
        print("CONVERSATION PASSED")
    else:
        print("CONVERSATION FAILED")

    return passed


def update_conversation(conversation, intent, message):
    """
    Update the conversation state based on the recognized intent.
    """

    text = message.lower()

    if intent == "symptom":
        conversation.add_symptom(message)

    elif intent == "location":
        conversation.set("location", message)

    elif intent == "duration":
        conversation.set("duration", message)

    elif intent == "severity":
        conversation.set("severity", message)

    elif intent == "medication":
        conversation.set("medication", message)

    elif intent == "image_upload":
        conversation.set("image_uploaded", True)


def test_basic_skin_conversation():
    messages = [
        "my skin is itchy",
        "it's on my arm",
        "for two weeks",
        "it's pretty bad",
        "i used moisturizer",
        "i can send a picture",
    ]

    expected = [
        "symptom",
        "location",
        "duration",
        "severity",
        "medication",
        "image_upload",
    ]

    return run_conversation(
        "TEST 1 — BASIC SKIN CONVERSATION",
        messages,
        expected
    )


def test_conversation_with_symptom_overlap():
    messages = [
        "there are red patches on my skin",
        "mostly on my face",
        "started three days ago",
        "the itching is really intense",
        "i already tried hydrocortisone",
        "here's a picture",
    ]

    expected = [
        "symptom",
        "location",
        "duration",
        "severity",
        "medication",
        "image_upload",
    ]

    return run_conversation(
        "TEST 2 — SYMPTOM / LOCATION OVERLAP",
        messages,
        expected
    )


def test_conversation_with_short_answers():
    messages = [
        "i have a rash",
        "my neck",
        "two weeks",
        "kinda bad",
        "no medication",
        "yes",
    ]

    expected = [
        "symptom",
        "location",
        "duration",
        "severity",
        "medication",
        "confirmation",
    ]

    return run_conversation(
        "TEST 3 — SHORT ANSWERS",
        messages,
        expected
    )


def test_emergency_interrupt():
    messages = [
        "my skin is itchy",
        "it's on my face",
        "my face is swelling up fast and i can barely breathe",
    ]

    expected = [
        "symptom",
        "location",
        "emergency",
    ]

    return run_conversation(
        "TEST 4 — EMERGENCY INTERRUPTION",
        messages,
        expected
    )


def test_goodbye_interrupt():
    messages = [
        "my skin is irritated",
        "on my arm",
        "gotta go, bye",
    ]

    expected = [
        "symptom",
        "location",
        "goodbye",
    ]

    return run_conversation(
        "TEST 5 — GOODBYE INTERRUPTION",
        messages,
        expected
    )


def test_confirmation():
    messages = [
        "my skin is red",
        "on my leg",
        "about two weeks",
        "it's getting worse",
        "i guess so",
    ]

    expected = [
        "symptom",
        "location",
        "duration",
        "severity",
        "confirmation",
    ]

    return run_conversation(
        "TEST 6 — CONFIRMATION",
        messages,
        expected
    )


if __name__ == "__main__":

    results = [
        test_basic_skin_conversation(),
        test_conversation_with_symptom_overlap(),
        test_conversation_with_short_answers(),
        test_emergency_interrupt(),
        test_goodbye_interrupt(),
        test_confirmation(),
    ]

    print("\n====================================")
    print("FINAL RESULTS")
    print("====================================")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Accuracy: {(passed / total) * 100:.2f}%")

    if passed == total:
        print("ALL CONVERSATION TESTS PASSED!")
    else:
        print("SOME CONVERSATION TESTS FAILED!")