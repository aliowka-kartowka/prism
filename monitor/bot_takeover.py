import telebot
from telebot import types
import requests
import json
import os
import time
import re
import logging
from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    try:
        # Prefix with 'trial_' for better organization in Marzban
        raw_username = message.from_user.username or f"{message.from_user.id}"
        tg_username = f"trial_{raw_username}"
        
        welcome_text = (
            f"🚀 <b>Добро пожаловать в FreeNet Monster!</b>\n\n"
            f"Мы подготовили для вас персональный защищенный туннель для аккаунта: <code>{tg_username}</code>\n\n"
            f"🛡 <b>Почему выбирают нас?</b>\n"
            f"• <b>10 ГБ бесплатно</b>: Полноценный тест на 24 часа.\n"
            f"• <b>Скрытный протокол</b>: Используем VLESS + Reality (невидим для РКН).\n"
            f"• <b>Полная анонимность</b>: Никаких регистраций и логов.\n"
            f"• <b>Статус 24/7</b>: Следите за доступностью сайтов через наш <a href='https://t.me/FreeNetMonsterBot/start'>Мониторинг</a>.\n\n"
            f"⌛ <i>Настройка подключения...</i>"
        )
        bot.reply_to(message, welcome_text, parse_mode='HTML', disable_web_page_preview=True)
        
        user = create_user(tg_username)
        if user and 'subscription_url' in user:
            sub_url = user['subscription_url']
            # Use first config link for QR if available
            qr_content = user['links'][0] if (user.get('links') and len(user['links']) > 0) else sub_url
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={qr_content}&margin=10&bgcolor=ffffff"
            
            caption = (
                f"✅ <b>Ваш доступ готов!</b>\n\n"
                f"🔗 <b>Ссылка на подписку:</b>\n<code>{sub_url}</code>\n\n"
                f"📖 <b>Быстрая настройка:</b>\n"
                f"1️⃣ <b>Скачайте приложение:</b>\n"
                f"   - Android: <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>v2rayNG</a>\n"
                f"   - iOS: <a href='https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690'>V2Box</a>\n"
                f"2️⃣ <b>Импортируйте данные:</b>\n"
                f"   - Откройте приложение и нажмите '+'\n"
                f"   - Выберите 'Import config from QR' или скопируйте ссылку выше.\n"
                f"3️⃣ <b>Подключитесь и наслаждайтесь свободой!</b> 🌍"
            )
            
            try:
                bot.send_photo(message.chat.id, qr_url, caption=caption, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                bot.send_message(message.chat.id, caption, parse_mode='HTML')
        else:
            error_msg = user.get('error', 'Unknown error') if isinstance(user, dict) else 'Unknown error'
            bot.send_message(message.chat.id, f"❌ Ошибка подключения: {error_msg}. Попробуйте еще раз через минуту.")
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Error in send_welcome: {error_trace}")
        # Send error to admin
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"🚫 <b>Error in /start handler:</b>\n<code>{error_trace[:3500]}</code>", parse_mode='HTML')
            except: pass

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
        bot.send_message(message.chat.id, "❌ Не удалось получить статистику серверов.")

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        # Create a beautiful shareable result
        r = types.InlineQueryResultArticle(
            '1',
            '🌐 FreeNet Monster: Статус и VPN',
            types.InputTextMessageContent(
                "🌐 **FreeNet Monster**: Проверьте, какие сайты заблокированы в РФ, и получите 10 ГБ бесплатного VPN для обхода ограничений! \n\n"
                "🚀 Запустить мониторинг и получить VPN: https://t.me/FreeNetMonsterBot",
                parse_mode='Markdown'
            ),
            description="Поделиться мониторингом и ссылкой на 10 ГБ VPN",
            thumbnail_url="https://freenet.monster/app_icon.png" # Assuming this works
        )
        bot.answer_inline_query(inline_query.id, [r], cache_time=1)
    except Exception as e:
        logger.error(f"Inline query error: {e}")

if __name__ == '__main__':
    pid = os.getpid()
    print(f'🚀 FreeNet Bot is starting (PID: {pid})...')
    logger.info(f'Bot process started with PID: {pid}')
    bot.set_my_commands([
        telebot.types.BotCommand("start", "Запустить прокси и мониторинг"),
        telebot.types.BotCommand("status", "Проверить статус системы")
    ])
    bot.infinity_polling()
