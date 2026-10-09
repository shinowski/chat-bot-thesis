from model.chatbot import Chatbot

bot = Chatbot()

response = bot.reply("Hello")
print(response)
print(bot.reply("Hello"))
print(bot.reply("Hi"))
print(bot.reply("Hey"))

print(bot.reply("My skin is itchy"))
print(bot.reply("I have a rash"))
print(bot.reply("My skin is red"))
print(bot.reply("It burns"))
print(bot.reply("It is painful"))