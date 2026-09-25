from model.semantic_chatbot import SemanticChatbot


bot = SemanticChatbot()


test_messages = [
    "hello",
    "I have an itchy rash",
    "it's on my elbow",
    "for about 3 days",
    "it hurts a lot",
    "I haven't used any medication",
]


for message in test_messages:

    print("\nUSER:", message)

    result = bot.reply(message)

    print("BOT:", result["reply"])
    print("INTENT:", result["intent"])
    print(
        "CONFIDENCE:",
        round(result["confidence"], 4)
    )