import telebot
from telebot import types, apihelper
import requests
import json
import os
import time
import re
import logging
from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv

# Load environment variables (force override to ensure new token is picked up)
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration from .env
BOT_TOKEN = os.getenv('FREENET_BOT_TOKEN', '').strip()
ADMIN_ID = int(os.getenv('FREENET_ADMIN_ID', '0').strip() or 0)
ADMIN_USER = os.getenv('FREENET_ADMIN_USER', '').strip()
ADMIN_PASS = os.getenv('FREENET_ADMIN_PASS', '').strip()
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://127.0.0.1:8080').strip()
proxy_url = os.getenv('TELEGRAM_PROXY', '').strip()

if proxy_url:
    apihelper.proxy = {'https': proxy_url}
    logger.info(f"Using Telegram proxy: {proxy_url}")

# Debug log without exposing whole token
if BOT_TOKEN:
    logger.info(f"Bot token loaded (sanitized). Length: {len(BOT_TOKEN)}")

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
        # ADD MOSCOW MIRROR (Raw IP fallback)
        user['mirror_subscription_url'] = f"http://94.159.117.222/sub/{token_part}"
    
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
            return map_user_links(check_resp.json())
    except Exception as e:
        logger.error(f"Check user error: {e}")
    
    # Create new user if not exists (Trial)
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
    if not token: return None
    headers = {'Authorization': f'Bearer {token}'}
    try:
        users_resp = requests.get(f"{MARZBAN_URL}/api/users", headers=headers, timeout=15)
        if users_resp.status_code != 200: return None
        users = users_resp.json()
        now = datetime.now(timezone.utc)
        total_users = len(users)
        active_accounts = sum(1 for u in users if u.get('status') == 'active')
        online_now = 0
        for u in users:
            online_at = u.get('online_at')
            if online_at:
                try:
                    dt = datetime.fromisoformat(online_at.replace('Z', '+00:00'))
                    if (now - dt).total_seconds() < 300: online_now += 1
                except: pass
        return {"total": total_users, "active": active_accounts, "online": online_now}
    except: return None

# Crypto Pay Configuration
CRYPTOPAY_TOKEN = os.getenv('CRYPTOPAY_TOKEN')
PREMIUM_PRICE_USD = 5.0
PREMIUM_DAYS = 30

def create_crypto_invoice(amount_usd, description):
    if not CRYPTOPAY_TOKEN: return None
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN}
    data = {
        "asset": "USDT",
        "amount": str(amount_usd),
        "description": description,
        "currency_type": "fiat",
        "fiat": "USD"
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('result')
    except:
        return None
    return None

def check_crypto_invoice(invoice_id):
    if not CRYPTOPAY_TOKEN: return False
    url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            invoices = resp.json().get('result', {}).get('items', [])
            if invoices and invoices[0].get('status') == 'paid':
                return True
    except: pass
    return False

def upgrade_to_premium(username):
    token = get_token()
    if not token: return False
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    user_url = f"{MARZBAN_URL}/api/user/{username}"
    now = int(time.time())
    update_data = {
        "data_limit": 0,
        "expire": now + (PREMIUM_DAYS * 86400),
        "status": "active",
        "note": "PREMIUM_USER"
    }
    try:
        requests.post(f"{MARZBAN_URL}/api/user/{username}/reset", headers=headers, timeout=10)
        resp = requests.put(user_url, headers=headers, json=update_data, timeout=10)
        return resp.status_code == 200
    except: return False

@bot.callback_query_handler(func=lambda call: call.data == "buy_premium")
def handle_buy_premium(call):
    is_direct = hasattr(call, 'id') and call.id == "direct_buy"
    if not is_direct:
        bot.answer_callback_query(call.id)
    
    invoice = create_crypto_invoice(PREMIUM_PRICE_USD, "FreeNet Premium (1 month)")
    if invoice:
        pay_url = invoice.get('pay_url')
        invoice_id = invoice.get('invoice_id')
        text = (
            "✅ <b>Счёт в CryptoBot выставлен!</b>\n\n"
            "Оплатите покупку по ссылке ниже. После оплаты нажмите кнопку для проверки."
        )
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔗 ОПЛАТИТЬ В CRYPTOBOT", url=pay_url))
        keyboard.add(types.InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ОПЛАТУ", callback_data=f"check_pay:{invoice_id}"))
        
        if is_direct:
            bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=keyboard)
        else:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=keyboard)
    else:
        bot.send_message(call.message.chat.id, "❌ Ошибка создания счёта. Попробуйте позже.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"DEBUG: Received /start from {message.from_user.id}")
    try:
        # Check for deep linking parameters
        start_param = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        raw_username = message.from_user.username or f"{message.from_user.id}"
        tg_username = f"trial_{raw_username}"
        
        # Check if user already exists
        user = create_user(tg_username)
        if "error" in user:
            bot.send_message(message.chat.id, f"❌ Ошибка: {user['error']}")
            return

        if start_param == 'buy':
            # Jump straight to checkout
            class MockCall:
                def __init__(self, message, id):
                    self.message = message
                    self.id = id
            handle_buy_premium(MockCall(message, "direct_buy"))
            return

        is_premium = user.get('note') == "PREMIUM_USER"
        now = int(time.time())
        is_expired = user.get('expire') and (user['expire'] < now)
        is_exhausted = not is_premium and (user.get('used_traffic', 0) >= user.get('data_limit', 0) and user.get('data_limit', 0) > 0)

        if (is_expired or is_exhausted) and not is_premium:
            text = (
                "⌛ <b>Ваш пробный период окончен!</b>\n\n"
                "Чтобы продолжить пользоваться VPN без ограничений, переходите на <b>Premium</b>.\n\n"
                "💎 <b>Premium Пакет:</b>\n"
                "• <b>Безлимитный</b> трафик\n"
                "• Срок: <b>30 дней</b>\n"
                "• Цена: <b>$5 USD</b> (в TON/USDT)\n\n"
                "Нажмите кнопку ниже, чтобы оплатить через <b>CryptoBot</b>:"
            )
            keyboard = types.InlineKeyboardMarkup()
            pay_button = types.InlineKeyboardButton(text="🔥 КУПИТЬ ПРЕМИУМ ($5)", callback_data="buy_premium")
            keyboard.add(pay_button)
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=keyboard)
            return

        # Normal Flow
        sub_url = user['subscription_url']
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={sub_url}&margin=10&bgcolor=ffffff"
        status_text = "💎 <b>Ваш Premium активен!</b>" if is_premium else "🚀 <b>Ваш пробный доступ готов!</b>"
        
        caption = (
            f"{status_text}\n\n"
            f"🔗 <b>Ссылка на подписку:</b>\n<code>{sub_url}</code>\n\n"
            f"📖 Скопируйте ссылку и добавьте её в v2rayNG или Shadowrocket."
        )
        bot.send_photo(message.chat.id, qr_url, caption=caption, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in send_welcome: {traceback.format_exc()}")

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

if __name__ == '__main__':
    logger.info(f'Bot process started...')
    bot.set_my_commands([
        telebot.types.BotCommand("start", "Запустить прокси и мониторинг"),
        telebot.types.BotCommand("status", "Проверить статус системы")
    ])
    bot.infinity_polling()
