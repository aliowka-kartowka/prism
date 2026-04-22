from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse as urlparse
import json
import requests
import logging
import os
import mimetypes
import time
import threading
import random
import string
import hashlib
import hmac
import re
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a global Session for efficient connection pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Marzban Configuration
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://127.0.0.1:8080')
ADMIN_USER = os.getenv('FREENET_ADMIN_USER', "aliowka")
ADMIN_PASS = os.getenv('FREENET_ADMIN_PASS', "VpnAdmin123!")

# Trial limits tracked by Telegram ID (tg_id -> (timestamp, username))
TRIAL_LIMITS = {}
TRIAL_LOCK = threading.Lock()
TRIAL_DURATION = 86400 # 24 hours
BOT_TOKEN = os.getenv('FREENET_BOT_TOKEN', "8516762550:AAHcq9hVrsgPRQIe9vUQ6uUXi4GOyOQB-cQ")
FREENET_ADMIN_ID = 1131496447

# --- Global Status Tracking ---
CHECK_RESULTS = []
RESULTS_LOCK = threading.Lock()

def init_results():
    global CHECK_RESULTS
    defaults = []
    for d in ['freenet.monster', 'google.com', 'youtube.com', 'instagram.com', 'yandex.ru']:
        defaults.append({"target": d, "is_ok": True, "node": "Hetzner (Germany)"})
    CHECK_RESULTS = defaults

init_results()

# --- RKN Block Alert Background Thread ---
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": FREENET_ADMIN_ID, "text": message, "parse_mode": "Markdown"}
    try:
        session.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send TG alert: {e}")

class RKNMonitorThread(threading.Thread):
    def __init__(self, admin_id):
        super().__init__(daemon=True)
        self.admin_id = admin_id
        # Get Master URL from env if this is a worker node
        self.master_url = os.getenv('MASTER_URL')
    
    def run(self):
        logger.info("RKN Monitor Thread started...")
        # Dictionary to track last status of each domain for alerting
        # Only alert for freenet.monster for now to avoid spam
        critical_domains = {'freenet.monster', 'www.freenet.monster'}
        last_statuses = {d: True for d in critical_domains}
        
        while True:
            try:
                results = []
                # Check a subset or all ALLOWED_DOMAINS
                # To avoid long loops, we check the most important ones + some random ones
                priority_domains = {'freenet.monster', 'google.com', 'youtube.com', 'instagram.com', 'yandex.ru'}
                test_set = priority_domains.union(set(random.sample(list(ALLOWED_DOMAINS), min(10, len(ALLOWED_DOMAINS)))))
                
                for domain in test_set:
                    # Prepend https:// if not present
                    url = f"https://{domain}" if not domain.startswith('http') else domain
                    is_up = check_url(url, use_vpn=False)
                    results.append({"target": domain, "is_ok": is_up})
                    
                    # Alert logic for critical domains
                    if domain in last_statuses and is_up != last_statuses[domain]:
                        if not is_up:
                            msg = f"🔴 **ALERT: {domain} BLOCKED in Russia!**"
                            send_telegram_alert(msg)
                            logger.warning(f"RKN BLOCK DETECTED for {domain}!")
                        else:
                            msg = f"🟢 **RECOVERY: {domain} RESTORED!**"
                            send_telegram_alert(msg)
                            logger.info(f"RKN BLOCK CLEARED for {domain}.")
                        last_statuses[domain] = is_up

                # Update global state for this node
                with RESULTS_LOCK:
                    global CHECK_RESULTS
                    # Update or add local results
                    # If we are Moscow node, we'll label it as such in the master post
                    # But locally we just keep them
                    for res in results:
                        # Update existing or append
                        found = False
                        for existing in CHECK_RESULTS:
                            if existing.get('target') == res['target'] and existing.get('node') == 'Moscow (Russia)':
                                existing['is_ok'] = res['is_ok']
                                found = True
                                break
                        if not found:
                            res['node'] = 'Moscow (Russia)'
                            CHECK_RESULTS.append(res)

                # If we have a master URL, push the full report
                if self.master_url:
                    try:
                        update_url = f"{self.master_url.rstrip('/')}/api/update"
                        session.post(update_url, json=results, timeout=15)
                        logger.info(f"Status report sent to master: {len(results)} domains")
                    except Exception as e:
                        logger.error(f"Failed to report to master: {e}")

            except Exception as e:
                logger.error(f"Error in RKN Monitor loop: {e}")
            
            time.sleep(300) # Check every 5 minutes
# ------------------------------------------

try: import urllib3
except ImportError: from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
XRAY_SOCKS_PROXY = 'socks5h://127.0.0.1:1081'

ALLOWED_DOMAINS = {
    'freenet.monster', 'www.freenet.monster',
    'www.youtube.com', 'www.instagram.com', 'www.facebook.com', 'x.com',
    'discord.com', 't.me', 'www.whatsapp.com', 'www.netflix.com', 'www.spotify.com',
    'www.twitch.tv', 'www.tiktok.com', 'www.google.com', 'www.wikipedia.org',
    'www.pinterest.com', 'www.aliexpress.com', 'google.com', 'youtube.com',
    'facebook.com', 'instagram.com', 'baidu.com', 'wikipedia.org',
    'xvideos.com', 'whatsapp.com', 'amazon.com',
    'pornhub.com', 'xnxx.com', 'live.com', 'netflix.com',
    'tiktok.com', 'office.com', 'linkedin.com', 'bing.com',
    'twitch.tv', 'weather.com', 'naver.com', 'bilibili.com',
    'zoom.us', 'chatgpt.com', 'pinterest.com',
    'aliexpress.com', 'github.com', 'coccoc.com',
    'roblox.com', 'duckduckgo.com', 'badoo.com', 'vimeo.com',
    'globo.com', 'paypal.com', 'qq.com', 'hulu.com', 'accuweather.com',
    'cnn.com', 'msn.com', 'imdb.com', 'wordpress.com',
    'nytimes.com', 'apple.com', 'walmart.com', 'bbc.com',
    'booking.com', 'chase.com',
    'wellsfargo.com', 'capitalone.com', 'bankofamerica.com',
    'target.com', 'lowes.com',
    'usps.com', 'huffpost.com', 'dailymotion.com', 'soundcloud.com',
    'flickr.com', 'yelp.com', 'pandora.com', 'foxnews.com',
    'forbes.com', 'businessinsider.com',
    'www.pornhub.com', 'www.xvideos.com', 'www.youporn.com'
}

def check_url(url, use_vpn=False):
    proxies = None
    if use_vpn:
        proxies = {'http': XRAY_SOCKS_PROXY, 'https': XRAY_SOCKS_PROXY}
    try:
        # Use a longer timeout for VPN but keep direct checks relatively snappy
        to = 10.0 if use_vpn else 7.0
        
        # Avoid downloading entire payloads initially.
        resp = session.get(url, proxies=proxies, timeout=to, verify=False, allow_redirects=True, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        
        # Robust check: If we are checking freenet.monster, verify the server is Cloudflare
        # ISP splash pages usually have their own server headers (nginx, microhttpd, etc.)
        if 'freenet.monster' in url:
            server_header = resp.headers.get('Server', '').lower()
            if 'cloudflare' not in server_header:
                logger.warning(f"ISP Interception detected for {url}! Server header: {server_header}")
                resp.close()
                return False
        
        is_ok = resp.status_code < 400
        resp.close()
        return is_ok
    except Exception as e:
        # If it's a timeout, it's definitely a block/slowdown
        logger.error(f'Error checking {url} (VPN: {use_vpn}): {e}')
        return False

def get_marzban_token():
    url = f"{MARZBAN_URL}/api/admin/token"
    data = {'username': ADMIN_USER, 'password': ADMIN_PASS}
    try:
        response = session.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"Marzban Auth failed: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Marzban Auth exception: {e}")
    return None

def create_marzban_trial(username):
    token = get_marzban_token()
    if not token:
        return {"error": "Authentication failed"}
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    url = f"{MARZBAN_URL}/api/user"
    
    # First check if user already exists
    try:
        get_url = f"{MARZBAN_URL}/api/user/{username}"
        get_response = session.get(get_url, headers=headers, timeout=5)
        if get_response.status_code == 200:
            user = get_response.json()
            
            # Check if user needs renewal (expired or exhausted data)
            # data_limit is compared against used_traffic
            status = user.get('status', 'active')
            used = user.get('used_traffic', 0)
            limit = user.get('data_limit', 0)
            
            if status != 'active' or (limit > 0 and used >= limit):
                logger.info(f"Renewing trial for user {username}")
                # Reset used_traffic and extend expiration
                renewal_data = {
                    "data_limit": 10737418240, # 10GB
                    "expire": int(time.time() + 86400) # +24h
                }
                # Marzban PUT /api/user/{username} to update
                put_url = f"{MARZBAN_URL}/api/user/{username}"
                put_res = session.put(put_url, headers=headers, json=renewal_data, timeout=10)
                if put_res.status_code == 200:
                    user = put_res.json()
                    # After update, we might need to reset traffic if Marzban doesn't do it via payload 
                    # Actually some Marzban versions need a separate reset call or just setting data_limit
                    # We'll try to explicitly reset used_traffic if possible, but usually PUT does it if passed
                    # Wait! Marzban's PUT /api/user/{username} doesn't usually take used_traffic to reset.
                    # There is often a POST /api/user/{username}/reset_usage
                    session.post(f"{put_url}/reset_usage", headers=headers, timeout=5)
                    # Re-fetch to get clean state
                    get_response = session.get(get_url, headers=headers, timeout=5)
                    if get_response.status_code == 200:
                        user = get_response.json()

            return map_user_links(user)
    except Exception as e:
        logger.error(f"Error checking/renewing existing user: {e}")
    
    # User doesn't exist (e.g. 404), so create it
    # 10GB in bytes
    DATA_LIMIT = 10737418240 
    
    user_data = {
        "username": username,
        "data_limit": DATA_LIMIT,
        "expire": int(time.time() + 86400), # 1 day from now
        "proxies": {"vless": {}},
        "inbounds": {"vless": ["VLESS REALITY", "VLESS WS"]}
    }
    
    try:
        response = session.post(url, headers=headers, json=user_data, timeout=10)
        if response.status_code in (200, 201):
            user = response.json()
            return map_user_links(user)
        else:
            return {"error": f"Marzban error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def map_single_link(link, user_id='trial'):
    """Maps a single VLESS link to the correct IP/Domain based on transport."""
    if 'vless://' not in link:
        return link
        
    # Detect if this is the WebSocket inbound
    is_ws = 'type=ws' in link and 'path=%2Fvpn-ws' in link
    
    # Replace IP/host with public domain or raw IP
    if '@' in link:
        parts = link.split('@')
        host_part = parts[1].split('?')[0] if '?' in parts[1] else parts[1]
        query_part = parts[1].split('?')[1] if '?' in parts[1] else ""
        
        # Composition for WebSocket (CDN) vs REALITY (Direct)
        if is_ws:
            # Cloudflare CDN uses port 443 with TLS
            new_host_port = "vpn.freenet.monster:443"
            # Update security and add SNI for TLS through Cloudflare
            query_part = query_part.replace('security=none', 'security=tls')
            if 'sni=' not in query_part:
                query_part += '&sni=vpn.freenet.monster'
        else:
            # REALITY (Direct) MUST use the raw IP because Cloudflare proxy blocks it on port 2053
            port = host_part.split(':')[-1] if ':' in host_part else "2053"
            new_host_port = f"178.104.135.156:{port}"
        
        link = f"{parts[0]}@{new_host_port}?{query_part}" if query_part else f"{parts[0]}@{new_host_port}"
    
    # Change remark for branding
    label = "FreeNet CDN" if is_ws else "FreeNet Direct"
    remark = f"{label} ({user_id})"
    
    if '#' in link:
        link = re.sub(r'#.*$', f"#{remark}", link)
    else:
        link = f"{link}#{remark}"
    return link

def map_user_links(user):
    # Map internal/API subscription URL to public domain
    sub_url = user.get('subscription_url', '')
    if sub_url and '/sub/' in sub_url:
        token_part = sub_url.split('/sub/')[-1]
        user['subscription_url'] = f"https://vpn.freenet.monster/sub/{token_part}"
        # ADD MOSCOW MIRROR (Raw IP fallback)
        user['mirror_subscription_url'] = f"http://94.159.117.222/sub/{token_part}"
    
    user_id = user.get('username', 'trial')
    links = user.get('links', [])
    user['links'] = [map_single_link(link, user_id) for link in links]
    return user

def generate_singbox_config(user):
    """
    Generates a full Sing-box JSON configuration for a user, 
    including VLESS outbounds and automatic routing rules for Russia.
    """
    username = user.get('username', 'user')
    links = user.get('links', [])
    
    outbounds = []
    
    # helper to parse VLESS params
    def parse_vless(link):
        try:
            # vless://uuid@host:port?query#remark
            p = urlparse.urlparse(link)
            uuid = p.netloc.split('@')[0]
            host_port = p.netloc.split('@')[1]
            host = host_port.split(':')[0]
            port = int(host_port.split(':')[1]) if ':' in host_port else 443
            query = urlparse.parse_qs(p.query)
            return {
                "uuid": uuid,
                "host": host,
                "port": port,
                "query": {k: v[0] for k, v in query.items()}
            }
        except Exception as e:
            logger.error(f"Error parsing VLESS link for Sing-box: {e}")
            return None

    # 1. Add VLESS outbounds
    for link in links:
        if 'vless://' not in link:
            continue
            
        data = parse_vless(link)
        if not data:
            continue
            
        is_ws = data['query'].get('type') == 'ws'
        is_reality = data['query'].get('security') == 'reality'
        
        outbound = {
            "type": "vless",
            "tag": f"FreeNet-{'CDN' if is_ws else 'Direct'}",
            "server": data['host'],
            "server_port": data['port'],
            "uuid": data['uuid'],
            "packet_encoding": "xudp"
        }
        
        if is_reality:
            outbound["flow"] = "xtls-rprx-vision"
            outbound["tls"] = {
                "enabled": True,
                "server_name": data['query'].get('sni', 'yandex.ru'),
                "utls": {"enabled": True, "fingerprint": data['query'].get('fp', 'chrome')},
                "reality": {
                    "enabled": True,
                    "public_key": data['query'].get('pbk', ''),
                    "short_id": data['query'].get('sid', '')
                }
            }
        elif is_ws:
            outbound["tls"] = {
                "enabled": True,
                "server_name": "vpn.freenet.monster",
                "utls": {"enabled": True, "fingerprint": "chrome"}
            }
            outbound["transport"] = {
                "type": "ws",
                "path": data['query'].get('path', '/vpn-ws'),
                "headers": {"Host": "vpn.freenet.monster"}
            }
        
        outbounds.append(outbound)

    # 2. Add system outbounds
    outbounds.append({"type": "direct", "tag": "direct"})
    outbounds.append({"type": "dns", "tag": "dns-out"})
    outbounds.append({"type": "block", "tag": "block"})

    # 3. Construct full config
    config = {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query", "detour": "FreeNet-Direct"},
                {"tag": "dns-direct", "address": "8.8.8.8", "detour": "direct"},
                {"tag": "dns-block", "address": "rcode://success"}
            ],
            "rules": [
                {"outbound": "dns-direct", "disable_cache": True, "domain_suffix": [".ru", ".рф"]},
                {"outbound": "dns-direct", "geosite": ["ru"]}
            ]
        },
        "inbounds": [{"type": "tun", "tag": "tun-in", "interface_name": "tun0", "inet4_address": "172.19.0.1/30", "auto_route": True, "strict_route": True, "stack": "system", "sniff": True}],
        "outbounds": outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"geoip": ["private", "ru"], "outbound": "direct"},
                {"geosite": ["ru"], "outbound": "direct"},
                {"domain_suffix": [".ru", ".рф"], "outbound": "direct"}
            ],
            "final": "FreeNet-Direct",
            "auto_detect_interface": True
        }
    }
    return config

class Handler(BaseHTTPRequestHandler):
    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse.urlparse(self.path)

        if parsed.path == '/api/trial':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                return

            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                auth_data = json.loads(post_data)
                if self.verify_telegram(auth_data):
                    self.handle_telegram_trial(auth_data)
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Invalid Telegram Authentication"}')
            except Exception as e:
                logger.error(f"Error processing POST trial: {e}")
                try:
                    self.send_response(500)
                    self.send_cors()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
                except: pass

        elif parsed.path == '/api/update':
            # Receive status updates from Moscow node
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400); self.end_headers(); return
            
            try:
                data = json.loads(self.rfile.read(content_length).decode())
                # data is expected to be a list of results: [{"target": "...", "is_ok": bool, "node": "..."}]
                with RESULTS_LOCK:
                    global CHECK_RESULTS
                    # Filter out old Moscow results and append new ones
                    new_results = [r for r in CHECK_RESULTS if r.get('node') != 'Moscow (Russia)']
                    for item in data:
                        item['node'] = 'Moscow (Russia)' # Ensure node label is correct
                        new_results.append(item)
                    CHECK_RESULTS = new_results
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
                logger.info(f"Received status update from Moscow node: {len(data)} items")
            except Exception as e:
                logger.error(f"Error updating results from Moscow: {e}")
                self.send_response(500); self.end_headers()

    def verify_telegram(self, auth_data):
        # Verify hash from Telegram Login Widget
        if 'hash' not in auth_data:
            return False
        
        check_hash = auth_data['hash']
        data_check_arr = []
        for key, value in sorted(auth_data.items()):
            if key != 'hash':
                data_check_arr.append(f"{key}={value}")
        data_check_string = "\n".join(data_check_arr)

        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        hash_result = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hash_result == check_hash

    def handle_telegram_trial(self, auth_data):
        tg_id = str(auth_data.get('id'))
        if not tg_id:
            self.send_response(400)
            self.send_cors()
            self.end_headers()
            return

        # Ensure we always send CORS headers for the trial API
        def send_success(data):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def send_error(data, code=400):
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        with TRIAL_LOCK:
            limit_info = TRIAL_LIMITS.get(tg_id)
            if limit_info:
                last_time, last_username = limit_info
                if time.time() - last_time < TRIAL_DURATION:
                    user = create_marzban_trial(last_username)
                    if "error" not in user:
                        send_success(user)
                        return

        # Create or renew trial linked to TG ID
        username = f"tg_{tg_id}"
        user = create_marzban_trial(username)
        
        if "error" in user:
            send_error(user)
        else:
            with TRIAL_LOCK:
                TRIAL_LIMITS[tg_id] = (time.time(), username)
            send_success(user)

    def do_GET(self):
        parsed = urlparse.urlparse(self.path)

        if parsed.path.startswith('/sub/'):
            # Subscription Interceptor
            token = parsed.path.split('/')[-1]
            try:
                # 1. Fetch original from Marzban (local)
                marzban_sub_url = f"http://localhost:8080/sub/{token}"
                resp = requests.get(marzban_sub_url, timeout=5)
                if resp.status_code != 200:
                    self.send_response(resp.status_code)
                    self.end_headers()
                    return
                
                # 2. Decode base64
                raw_content = base64.b64decode(resp.text).decode('utf-8')
                lines = raw_content.strip().split('\n')
                
                # 3. Map each link
                mapped_lines = []
                for line in lines:
                    mapped_lines.append(map_single_link(line.strip()))
                
                # 4. Re-encode
                final_content = base64.b64encode('\n'.join(mapped_lines).encode()).decode()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_cors()
                self.end_headers()
                self.wfile.write(final_content.encode())
            except Exception as e:
                logger.error(f"Error in sub interceptor: {e}")
                self.send_response(500)
                self.end_headers()

        elif parsed.path == '/api/status':
            with RESULTS_LOCK:
                body = json.dumps(CHECK_RESULTS).encode()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors()
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/api/check':
            params = urlparse.parse_qs(parsed.query)
            target_url = params.get('url', [''])[0]
            use_vpn = params.get('use_vpn', ['false'])[0].lower() == 'true'

            if not target_url:
                self.send_response(400)
                self.end_headers()
                return

            try:
                parsed_url = urlparse.urlparse(target_url)
                domain = parsed_url.netloc
                if domain not in ALLOWED_DOMAINS:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Forbidden site"}')
                    return
            except:
                self.send_response(400)
                self.end_headers()
                return

            is_up = check_url(target_url, use_vpn=use_vpn)
            body = json.dumps({'up': is_up, 'status': 'up' if is_up else 'down'}).encode()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/api/logs':
            # Simple security: check for token in query params
            params = urlparse.parse_qs(parsed.query)
            token = params.get('token', [''])[0]
            
            if not token or token != ADMIN_PASS:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return

            try:
                log_file = 'server.log'
                if os.path.exists(log_file):
                    # Read last 300 lines and filter out noisy requests
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                    
                    # Filter: ignore /api/logs, /api/marzban, /api/status, /api/update and anything with token=
                    filtered_lines = []
                    # We look at more lines initially because many might be filtered out
                    for line in lines[-400:]:
                        if any(x in line for x in ['/api/logs', 'token=', '/api/marzban', '/api/status', '/api/update']):
                            continue
                        filtered_lines.append(line)
                    
                    body = json.dumps({'logs': filtered_lines[-150:]}).encode()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()
            except Exception as e:
                logger.error(f"Error reading logs: {e}")
                self.send_response(500)
                self.end_headers()

        elif parsed.path == '/api/marzban/users':
            token = urlparse.parse_qs(parsed.query).get('token', [''])[0]
            if token != ADMIN_PASS:
                self.send_response(401); self.end_headers(); return
            
            m_token = get_marzban_token()
            if not m_token:
                self.send_response(500); self.end_headers(); return
            
            try:
                headers = {'Authorization': f'Bearer {m_token}'}
                resp = session.get(f"{MARZBAN_URL}/api/users", headers=headers, params={'sort': '-used_traffic'}, timeout=10)
                logger.info(f"Marzban stats fetch: {resp.status_code}")
                self.send_response(resp.status_code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(resp.content)
            except Exception as e:
                logger.error(f"Error fetching Marzban users: {e}")
                self.send_response(500); self.end_headers()

        elif parsed.path == '/api/marzban/logs':
            token = urlparse.parse_qs(parsed.query).get('token', [''])[0]
            if token != ADMIN_PASS:
                self.send_response(401); self.end_headers(); return
            
            m_token = get_marzban_token()
            
            # Try to fetch from API first
            log_content = ""
            if m_token:
                headers = {'Authorization': f'Bearer {m_token}'}
                # Try multiple possible endpoints for Marzban logs
                for endpoint in ['/api/core/logs', '/api/system/logs']:
                    try:
                        resp = session.get(f"{MARZBAN_URL}{endpoint}", headers=headers, timeout=5)
                        logger.info(f"Marzban fetch {endpoint}: {resp.status_code}")
                        if resp.status_code == 200:
                            log_content = resp.json().get('logs', "")
                            if log_content: break
                    except Exception as e:
                        logger.error(f"Error fetching Marzban logs from {endpoint}: {e}")

            # Fallback: if API failed or empty, try Docker logs directly (if on Hetzner)
            if not log_content:
                logger.info("Attempting fallback to Docker logs for Marzban")
                try:
                    import subprocess
                    # Fetch last 150 lines from docker
                    res = subprocess.run(["sudo", "docker", "logs", "--tail", "150", "marzban"], 
                                         capture_output=True, text=True, timeout=5)
                    log_content = res.stdout + "\n" + res.stderr
                except Exception as e:
                    log_content = f"Error: Could not fetch Marzban logs via API or Docker. {e}"
                    logger.error(log_content)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"logs": log_content.splitlines()}).encode())

        elif parsed.path == '/api/trial':
            # Prioritize X-Real-IP or X-Forwarded-For if behind a proxy
            client_ip = self.headers.get('X-Real-IP')
            if not client_ip:
                forwarded = self.headers.get('X-Forwarded-For')
                if forwarded:
                    client_ip = forwarded.split(',')[0].strip()
                else:
                    client_ip = self.client_address[0]
            
            logger.info(f"Trial request from IP: {client_ip}")
            
            with TRIAL_LOCK:
                limit_info = TRIAL_LIMITS.get(client_ip)
                if limit_info:
                    last_time, last_username = limit_info
                    if time.time() - last_time < TRIAL_DURATION:
                        # Fetch existing user instead of error
                        user = create_marzban_trial(last_username) # This will fetch if it exists
                        if "error" not in user:
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.send_cors()
                            self.end_headers()
                            self.wfile.write(json.dumps(user).encode())
                            return
                        # If fetch failed (e.g. user deleted), allow creating new one
                        del TRIAL_LIMITS[client_ip]

                # Set limit temporarily (placeholder username)
                TRIAL_LIMITS[client_ip] = (time.time(), "")

            # Generate random username
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            username = f"user_{suffix}"
            
            user = create_marzban_trial(username)
            if "error" in user:
                # Reset limit on error so user can try again
                with TRIAL_LOCK:
                    if client_ip in TRIAL_LIMITS:
                        del TRIAL_LIMITS[client_ip]
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps(user).encode())
            else:
                # Update limit with actual username
                with TRIAL_LOCK:
                    TRIAL_LIMITS[client_ip] = (TRIAL_LIMITS[client_ip][0], username)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps(user).encode())
        
        elif parsed.path.startswith('/api/config/singbox/'):
            username = parsed.path.split('/')[-1]
            # Verify if user exists 
            user = create_marzban_trial(username) # Fetches existing
            if "error" in user:
                self.send_response(404)
                self.send_cors()
                self.end_headers()
                self.wfile.write(b'{"error": "User not found"}')
            else:
                config = generate_singbox_config(user)
                body = json.dumps(config, indent=2).encode()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Disposition', f'attachment; filename="freenet_{username}.json"')
                self.send_cors()
                self.end_headers()
                self.wfile.write(body)

        elif parsed.path in ('/', '/index.html'):
            self._serve_file('index.html', 'text/html; charset=utf-8')

        elif parsed.path in ('/console', '/console.html'):
            self._serve_file('console.html', 'text/html; charset=utf-8')

        else:
            # Serve any other static file from STATIC_DIR
            filename = parsed.path.lstrip('/')
            if not filename: filename = 'index.html'
            self._serve_file(filename, 'text/html; charset=utf-8')

    def log_message(self, format, *args):
        # Ignore repetitive polling logs for the console and stats
        try:
            request_line = args[0]
            # Filter matches both /api/logs and /api/marzban and any request with token
            if any(x in request_line for x in ['/api/logs', '/api/marzban', 'token=', '/api/status', '/api/update']):
                return
        except:
            pass
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format%args))

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(STATIC_DIR, filename)
        try:
            with open(filepath, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    # Start RKN Monitor
    rkn_thread = RKNMonitorThread(admin_id=1131496447)
    rkn_thread.start()

    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(('0.0.0.0', 8090), Handler)
    print('Russia Multi-Threaded Monitor running on port 8090...')
    server.serve_forever()
