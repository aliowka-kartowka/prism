import telebot
import requests
import json
import os
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/home/aliowka/workspace/prism/.env')

# Configuration from .env
BOT_TOKEN = os.getenv('FREENET_BOT_TOKEN')
ADMIN_ID = int(os.getenv('FREENET_ADMIN_ID', 0))
ADMIN_USER = os.getenv('FREENET_ADMIN_USER')
ADMIN_PASS = os.getenv('FREENET_ADMIN_PASS')
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://127.0.0.1:8080')

bot = telebot.TeleBot(BOT_TOKEN)

def get_token():
    url = f"{MARZBAN_URL}/api/admin/token"
    data = {'username': ADMIN_USER, 'password': ADMIN_PASS}
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"Auth failed: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Auth exception: {e}")
    return None

def create_user(username):
    token = get_token()
    if not token:
        return {"error": "Authentication failed"}
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    user_url = f"{MARZBAN_URL}/api/user/{username}"
    try:
        check_resp = requests.get(user_url, headers=headers, timeout=10)
        if check_resp.status_code == 200:
            return check_resp.json()
    except Exception as e:
        logger.error(f"Check user exception: {e}")
    
    url = f"{MARZBAN_URL}/api/user"
    user_data = {
        "username": username,
        "proxies": {"vless": {}},
        "inbounds": {"vless": ["VLESS TCP REALITY"]}
    }
    
    try:
        response = requests.post(url, headers=headers, json=user_data, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_detailed_stats():
    token = get_token()
    if not token:
        logger.error("Could not get token for stats")
        return None
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        logger.info(f"Fetching users from {MARZBAN_URL}/api/users")
        users_resp = requests.get(f"{MARZBAN_URL}/api/users", headers=headers, timeout=15)
        if users_resp.status_code != 200:
            logger.error(f"Users request failed: {users_resp.status_code} {users_resp.text}")
            return None
        
        users = users_resp.json()
        # Some versions return {"users": [...], "total": ...}
        if isinstance(users, dict) and 'users' in users:
            users = users['users']
            
        now = datetime.now(timezone.utc)
        total_users = len(users)
        active_accounts = 0
        online_now = 0
        
        for u in users:
            if not isinstance(u, dict):
                continue
            if u.get('status') == 'active':
                active_accounts += 1
            
            online_at = u.get('online_at')
            if online_at:
                try:
                    dt = datetime.fromisoformat(online_at.replace('Z', '+00:00'))
                    diff = (now - dt).total_seconds()
                    if diff < 300: 
                        online_now += 1
                except:
                    pass
        
        return {"total": total_users, "active": active_accounts, "online": online_now}
    except Exception as e:
        logger.error(f"Stats exception: {e}")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    tg_username = message.from_user.username
    if not tg_username:
        bot.reply_to(message, "❌ Please set a Telegram username first!")
        return

    bot.reply_to(message, f"Welcome to FreeNet Monster! 🚀\n\nI am setting up your secure private connection (Username: {tg_username})...")
    
    user = create_user(tg_username)
    if 'subscription_url' in user:
        sub_url = user['subscription_url']
        public_sub_url = sub_url.replace('http://127.0.0.1:8080', 'https://vpn.freenet.monster')
        bot.send_message(message.chat.id, f"✅ Your account is ready!\n\nYour Subscription Link:\n`{public_sub_url}`\n\n1. Install **v2rayNG** (Android) or **V2BOX** (iOS).\n2. Import this link.\n3. Enjoy freedom! 🌍", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Connection error. Please try again in 1 minute.")

@bot.message_handler(commands=['status'])
def send_status(message):
    logger.info(f"Status command received from {message.from_user.username}")
    stats = get_detailed_stats()
    
    if stats:
        resp = "🛡 **FreeNet Monster Status**\n\n"
        resp += f"👥 Total Users: `{stats['total']}`\n"
        resp += f"✅ Active Accounts: `{stats['active']}`\n"
        resp += f"🔥 Currently Connected: `{stats['online']}`\n"
        resp += "\nAll nodes are running smoothly. ✅"
        bot.send_message(message.chat.id, resp, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Failed to retrieve live statistics.")

if __name__ == '__main__':
    logger.info('FreeNet Takeover Bot is starting...')
    bot.infinity_polling()
