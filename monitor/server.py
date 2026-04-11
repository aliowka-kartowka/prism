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

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
XRAY_SOCKS_PROXY = 'socks5h://127.0.0.1:1081'

def check_url(url, use_vpn=False):
    proxies = None
    if use_vpn:
        proxies = {'http': XRAY_SOCKS_PROXY, 'https': XRAY_SOCKS_PROXY}
    try:
        logger.info(f'Checking {url} (VPN: {use_vpn})')
        resp = requests.get(url, proxies=proxies, timeout=10, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
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
