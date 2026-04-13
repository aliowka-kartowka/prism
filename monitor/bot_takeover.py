import telebot
import requests
import json
import os
import time
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
BOT_TOKEN = os.getenv('FREENET_BOT_TOKEN')
ADMIN_ID = int(os.getenv('FREENET_ADMIN_ID', 0))
ADMIN_USER = os.getenv('FREENET_ADMIN_USER')
ADMIN_PASS = os.getenv('FREENET_ADMIN_PASS')
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://127.0.0.1:8080')

bot = telebot.TeleBot(BOT_TOKEN)

def get_token():
    url = f"{MARZBAN_URL}/api/admin/token"
    # Note: Marzban uses form-data or JSON depending on version, usually form-data for login
    data = {
        'username': ADMIN_USER,
        'password': ADMIN_PASS
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()['access_token']
    except Exception as e:
        print(f"Token error: {e}")
    return None

def map_user_links(user):
    # Map internal/API subscription URL to public domain
    sub_url = user.get('subscription_url', '')
    if sub_url and '/sub/' in sub_url:
        token_part = sub_url.split('/sub/')[-1]
        user['subscription_url'] = f"https://vpn.freenet.monster/sub/{token_part}"
    
    # Also update protocol links to use the public domain and rebrand remark
    username = user.get('username', 'trial')
    remark = f"FreeNet ({username})"
    links = user.get('links', [])
    new_links = []
    for link in links:
        if 'vless://' in link:
            # Replace IP/host with public domain
            if '@' in link:
                parts = link.split('@')
                if '/' in parts[1]:
                    host_port, rest = parts[1].split('/', 1)
                else:
                    host_port = parts[1]
                    rest = ""
                
                if ':' in host_port:
                    port = host_port.split(':')[-1]
                else:
                    port = "443"
                
                new_host_port = f"vpn.freenet.monster:{port}"
                link = f"{parts[0]}@{new_host_port}/{rest}"
            
            # Rebrand remark
            if '#' in link:
                link = re.sub(r'#.*$', f"#{remark}", link)
            else:
                link = f"{link}#{remark}"
        new_links.append(link)
    user['links'] = new_links
    return user

def create_user(username, data_limit=10737418240, expire_days=1):
    token = get_token()
    if not token:
        return {"error": "Authentication failed"}
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Check if user exists
    user_url = f"{MARZBAN_URL}/api/user/{username}"
    try:
        check_resp = requests.get(user_url, headers=headers, timeout=10)
        if check_resp.status_code == 200:
            user = check_resp.json()
            
            # Automatic Renewal: If user is expired or nearly expired, refresh them
            # Also reset data usage if it's exhausted
            now = int(time.time())
            needs_update = False
            update_data = {}
            
            if user.get('expire') and (user['expire'] < now + 3600): # Expired or expiring in 1h
                update_data['expire'] = now + (expire_days * 86400)
                update_data['data_limit'] = 10737418240 # Ensure 10GB on renewal
                update_data['status'] = 'active'
                needs_update = True
                
            if user.get('used_traffic', 0) >= user.get('data_limit', 0):
                # Reset usage by setting to 0? Marzban PUT /user doesn't reset usage directly,
                # but we can increase the limit or recreate. 
                # Actually, most agents prefer resetting via 'reset' endpoint.
                try:
                    requests.post(f"{MARZBAN_URL}/api/user/{username}/reset", headers=headers, timeout=10)
                except: pass
                needs_update = True

            if needs_update:
                requests.put(user_url, headers=headers, json=update_data, timeout=10)
                # Fetch fresh data after update
                check_resp = requests.get(user_url, headers=headers, timeout=10)
                user = check_resp.json()
                
            return map_user_links(user)
    except Exception as e:
        print(f"Check user error: {e}")
    
    # Create new user if not exists
    url = f"{MARZBAN_URL}/api/user"
    user_data = {
        "username": username,
        "data_limit": data_limit,
        "expire": int(time.time() + (expire_days * 86400)),
        "proxies": {"vless": {}},
        "inbounds": {"vless": ["VLESS REALITY"]}
    }
    
    try:
        response = requests.post(url, headers=headers, json=user_data, timeout=10)
        if response.status_code in (200, 201):
            return map_user_links(response.json())
        return {"error": f"Marzban error {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_detailed_stats():
    token = get_token()
    if not token:
        return None
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        users_resp = requests.get(f"{MARZBAN_URL}/api/users", headers=headers, timeout=15)
        if users_resp.status_code != 200:
            return None
        
        users = users_resp.json()
        now = datetime.now(timezone.utc)
        
        total_users = len(users)
        active_accounts = 0
        online_now = 0
        
        for u in users:
            if u.get('status') == 'active':
                active_accounts += 1
            
            online_at = u.get('online_at')
            if online_at:
                try:
                    dt = datetime.fromisoformat(online_at.replace('Z', '+00:00'))
                    diff = (now - dt).total_seconds()
                    if diff < 300: # 5 minutes
                        online_now += 1
                except:
                    pass
        
        return {
            "total": total_users,
            "active": active_accounts,
            "online": online_now
        }
    except:
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Prefix with 'trial_' for better organization in Marzban
    raw_username = message.from_user.username or f"{message.from_user.id}"
    tg_username = f"trial_{raw_username}"
    
    # Check if this is a trial request from monitor (deep link)
    is_monitor = "monitor" in message.text
    
    welcome_text = (
        f"Welcome to FreeNet Monster! 🚀\n\n"
        f"I am setting up your secure private connection for account: **{tg_username}**..."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')
    
    user = create_user(tg_username)
    if user and 'subscription_url' in user:
        sub_url = user['subscription_url']
        # Use first config link for QR if available
        qr_content = user['links'][0] if (user.get('links') and len(user['links']) > 0) else sub_url
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={qr_content}&margin=10&bgcolor=ffffff"
        
        caption = (
            f"✅ **Your account is ready!**\n\n"
            f"Your Subscription Link:\n`{sub_url}`\n\n"
            f"1. **Scan the QR code above** or copy the link.\n"
            f"2. Import into **v2rayNG** (Android) or **V2BOX** (iOS).\n"
            f"3. Connect and enjoy freedom! 🌍"
        )
        
        try:
            bot.send_photo(message.chat.id, qr_url, caption=caption, parse_mode='Markdown')
        except Exception:
            bot.send_message(message.chat.id, caption, parse_mode='Markdown')
    else:
        error_msg = user.get('error', 'Unknown error') if isinstance(user, dict) else 'Unknown error'
        bot.send_message(message.chat.id, f"❌ Connection error: {error_msg}. Please try again in 1 minute.")

@bot.message_handler(commands=['status'])
def send_status(message):
    stats = get_detailed_stats()
    if stats:
        resp = (
            "🛡 **FreeNet Monster Status**\n\n"
            f"👥 Total Users: `{stats['total']}`\n"
            f"✅ Active Accounts: `{stats['active']}`\n"
            f"🔥 Online Now: `{stats['online']}`\n\n"
            "All nodes are running smoothly. ✅"
        )
        bot.send_message(message.chat.id, resp, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Failed to retrieve live statistics.")

if __name__ == '__main__':
    print('FreeNet Bot is starting...')
    bot.set_my_commands([
        telebot.types.BotCommand("start", "Initialize connection"),
        telebot.types.BotCommand("status", "System stats")
    ])
    bot.infinity_polling()
