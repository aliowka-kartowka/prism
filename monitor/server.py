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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Marzban Configuration
MARZBAN_URL = os.getenv('MARZBAN_URL', 'http://178.104.135.156:8080')
ADMIN_USER = os.getenv('FREENET_ADMIN_USER')
ADMIN_PASS = os.getenv('FREENET_ADMIN_PASS')

# Rate limiting for trials: 1 per IP per 24 hours
TRIAL_LIMITS = {}
TRIAL_LOCK = threading.Lock()
TRIAL_DURATION = 86400 # 24 hours in seconds

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
XRAY_SOCKS_PROXY = 'socks5h://127.0.0.1:1081'

ALLOWED_DOMAINS = {
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
        # Avoid downloading entire payloads initially
        resp = requests.head(url, proxies=proxies, timeout=3.5, verify=False, allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        
        # If the server rejects HEAD requests (e.g., Yahoo returns 404/405 for HEAD), fallback to an aborted GET request
        if resp.status_code >= 400:
            resp = requests.get(url, proxies=proxies, timeout=3.5, verify=False, allow_redirects=True, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
            resp.close() # Close connection immediately after receiving headers
            
        return resp.status_code < 400
    except Exception as e:
        logger.error(f'Error checking {url} (VPN: {use_vpn}): {e}')
        return False

def get_marzban_token():
    url = f"{MARZBAN_URL}/api/admin/token"
    data = {'username': ADMIN_USER, 'password': ADMIN_PASS}
    try:
        response = requests.post(url, data=data, timeout=10)
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
    
    # 1GB in bytes
    DATA_LIMIT = 1073741824 
    
    user_data = {
        "username": username,
        "data_limit": DATA_LIMIT,
        "expire": int(time.time() + 86400), # 1 day from now
        "proxies": {"vless": {}}
    }
    
    try:
        response = requests.post(url, headers=headers, json=user_data, timeout=10)
        if response.status_code in (200, 201):
            user = response.json()
            # Map internal/API subscription URL to public domain
            sub_url = user.get('subscription_url', '')
            if sub_url and '/sub/' in sub_url:
                token_part = sub_url.split('/sub/')[-1]
                user['subscription_url'] = f"https://vpn.freenet.monster/sub/{token_part}"
            
            # Also update protocol links to use the public domain if they have an IP or localhost
            links = user.get('links', [])
            new_links = []
            for link in links:
                if 'vless://' in link:
                    # Replace IP/host with public domain in vless links
                    # vless://uuid@IP:PORT?... -> vless://uuid@vpn.freenet.monster:PORT?...
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
                            port = "443" # Default
                        
                        new_host_port = f"vpn.freenet.monster:{port}"
                        link = f"{parts[0]}@{new_host_port}/{rest}"
                new_links.append(link)
            user['links'] = new_links
            return user
        else:
            return {"error": f"Marzban error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse.urlparse(self.path)

        if parsed.path == '/api/check':
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
                last_time = TRIAL_LIMITS.get(client_ip, 0)
                if time.time() - last_time < TRIAL_DURATION:
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Rate limit exceeded. 1 trial per 24 hours."}).encode())
                    return
                # Set limit temporarily
                TRIAL_LIMITS[client_ip] = time.time()

            # Generate random username
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            username = f"FreeNet-trial_{suffix}"
            
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
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.end_headers()
                self.wfile.write(json.dumps(user).encode())

        elif parsed.path in ('/', '/index.html'):
            self._serve_file('index.html', 'text/html; charset=utf-8')

        else:
            # Serve any other static file from STATIC_DIR
            filename = parsed.path.lstrip('/')
            filepath = os.path.join(STATIC_DIR, filename)
            if os.path.isfile(filepath) and os.path.abspath(filepath).startswith(STATIC_DIR):
                mime, _ = mimetypes.guess_type(filepath)
                self._serve_file(filename, mime or 'application/octet-stream')
            else:
                self.send_response(404)
                self.end_headers()

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
    server = ThreadingHTTPServer(('0.0.0.0', 8090), Handler)
    print('Russia Multi-Threaded Monitor running on port 8090...')
    server.serve_forever()
