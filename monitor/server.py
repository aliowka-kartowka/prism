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

# Create a global Session for efficient connection pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)
session.mount('https://', adapter)

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
        # Avoid downloading entire payloads initially. Use the global session for pooling.
        resp = session.head(url, proxies=proxies, timeout=3.5, verify=False, allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        
        # If the server rejects HEAD requests, fallback to an aborted GET request
        if resp.status_code >= 400:
            resp = session.get(url, proxies=proxies, timeout=3.5, verify=False, allow_redirects=True, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
            resp.close() # Close connection immediately after receiving headers
            
        return resp.status_code < 400
    except Exception as e:
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
        "inbounds": {"vless": ["VLESS REALITY"]}
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

def map_user_links(user):
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
            
            # Change remark to FreeNet (username) for better identification
            import re
            user_id = user.get('username', 'trial')
            remark = f"FreeNet ({user_id})"
            if '#' in link:
                link = re.sub(r'#.*$', f"#{remark}", link)
            else:
                link = f"{link}#{remark}"
        new_links.append(link)
    user['links'] = new_links
    return user

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
