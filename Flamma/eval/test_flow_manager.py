from model.flow_manager import FlowManager
from model.conversation import Conversation


flow = FlowManager()
conversation = Conversation()

print("====================================")
print("     FLOW MANAGER INTENT TEST")
print("====================================")


def test_expected(label, expected):
    result = flow.get_expected_intent(conversation)

    print()
    print("Current expected:", result)
    print("Expected:", expected)

    if result == expected:
        print("PASS")
    else:
        print("FAIL")


# 1. Nothing collected yet
test_expected("initial", "symptom")


# 2. Add symptom
conversation.add_symptom("itchy skin")
test_expected("after symptom", "location")


# 3. Add location
conversation.set("location", "arm")
test_expected("after location", "duration")


# 4. Add duration
conversation.set("duration", "two weeks")
test_expected("after duration", "medication")


# 5. Severity is optional and does not add a screening step
conversation.set("severity", "moderate")
test_expected("after severity", "medication")


# 6. Add medication
conversation.set("medication", "none")
test_expected("after medication", "image_upload")


# 7. Upload image
conversation.data["image_uploaded"] = True
test_expected("after image", None)


print()
print("====================================")
print("        TEST COMPLETE")
print("====================================")
