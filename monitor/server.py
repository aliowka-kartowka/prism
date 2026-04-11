from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse as urlparse
import json
import requests
import logging
import os
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    'samsung.com', 'roblox.com', 'duckduckgo.com', 'badoo.com', 'vimeo.com',
    'globo.com', 'paypal.com', 'qq.com', 'hulu.com', 'accuweather.com',
    'cnn.com', 'msn.com', 'imdb.com', 'wordpress.com',
    'nytimes.com', 'apple.com', 'walmart.com', 'bbc.com', 'craigslist.org',
    'booking.com', 'imgur.com', 'chase.com',
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
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(body))
            self.send_cors()
            self.end_headers()
            self.wfile.write(body)

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
