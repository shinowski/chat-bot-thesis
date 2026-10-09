from model.conversation import Conversation

memory = Conversation()

print(memory.show())

memory.set("symptom", "itchy")

memory.set("location", "arm")

print(memory.show())