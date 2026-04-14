import telebot
import os
from dotenv import load_dotenv

load_dotenv('/home/aliowka/workspace/prism/.env')
token = os.getenv('FREENET_BOT_TOKEN')
admin_id = os.getenv('FREENET_ADMIN_ID')

bot = telebot.TeleBot(token)
try:
    print(f"Testing bot with token {token[:10]}...")
    bot.send_message(admin_id, "TEST: Bot is alive and can send messages!")
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
