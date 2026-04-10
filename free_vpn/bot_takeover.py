from dotenv import load_dotenv
import telebot
import requests
import os
import json
import time

load_dotenv()

API_TOKEN = os.getenv('FREENET_BOT_TOKEN')
ADMIN_ID = int(os.getenv('FREENET_ADMIN_ID', '0'))
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://localhost:8080')
ADMIN_USERNAME = os.getenv('FREENET_ADMIN_USER')
ADMIN_PASSWORD = os.getenv('FREENET_ADMIN_PASS')

bot = telebot.TeleBot(API_TOKEN)
access_token = None
token_expiry = 0

def get_access_token():
    global access_token, token_expiry
    if access_token and time.time() < token_expiry:
        return access_token
        
    try:
        response = requests.post(f'{MARZBAN_URL}/api/admin/token', data={'username': ADMIN_USERNAME, 'password': ADMIN_PASSWORD})
        data = response.json()
        access_token = data['access_token']
        token_expiry = time.time() + 3000
        return access_token
    except Exception as e:
        print(f'Error getting token: {e}')
        return None

def create_user(username):
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    user_data = {
        "username": username,
        "proxies": {"vless": {}},
        "inbounds": {"vless": ["VLESS REALITY"]},
        "data_limit": 10 * 1024 * 1024 * 1024,
        "expire": 0
    }
    check = requests.get(f'{MARZBAN_URL}/api/user/{username}', headers=headers)
    if check.status_code == 200:
        return check.json()
        
    response = requests.post(f'{MARZBAN_URL}/api/user', headers=headers, json=user_data)
    return response.json()

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Welcome back, Creator. 👑\n\nYou have full control. Auto-delivery is ACTIVE for all new users.")
    else:
        tg_username = f'tg_{message.from_user.id}'
        bot.reply_to(message, f"Welcome to Spirit VPN! 🚀\n\nI am setting up your secure private connection (Username: {tg_username})...")
        
        try:
            user = create_user(tg_username)
            if 'subscription_url' in user:
                sub_url = user['subscription_url']
                public_sub_url = sub_url.replace('http://127.0.0.1:8080', 'https://vpn.freenet.monster')
                bot.send_message(message.chat.id, f"✅ Your account is ready!\n\nYour Subscription Link:\n`{public_sub_url}`\n\n1. Install **v2rayNG** (Android) or **V2BOX** (iOS).\n2. Import this link.\n3. Enjoy freedom! 🌍", parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "❌ Connection error. Please try again in 1 minute.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

if __name__ == '__main__':
    print('Freenet Takeover Bot is starting...')
    bot.infinity_polling()