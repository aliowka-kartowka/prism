#!/usr/bin/env python3
"""
Russia Internet Monitor - Backend API Server
Runs on Moscow server, checks sites, serves HTML + JSON API
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
import urllib.request
import json
import ssl
import threading

# Disable warnings for verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ALLOWED_DOMAINS = {
    'flickr.com',
    'www.netflix.com',
    'roblox.com',
    'tripadvisor.com',
    'samsung.com',
    'forbes.com',
    'fandom.com',
    'bilibili.com',
    'espn.com',
    'huffpost.com',
    'naver.com',
    'github.com',
    'netflix.com',
    'live.com',
    'xhamster.com',
    'tiktok.com',
    'hulu.com',
    'cnbc.com',
    'google.com',
    'booking.com',
    'paypal.com',
    'pornhub.com',
    'www.youporn.com',
    'amazon.com',
    'mail.ru',
    'qq.com',
    'nytimes.com',
    'xnxx.com',
    'wikipedia.org',
    'wsj.com',
    'www.pornhub.com',
    'badoo.com',
    'dailymotion.com',
    'dzen.ru',
    'vk.com',
    'www.whatsapp.com',
    'max.com',
    'baidu.com',
    'usps.com',
    'craigslist.org',
    'imdb.com',
    'xvideos.com',
    'wordpress.com',
    'homedepot.com',
    'youtube.com',
    'cnn.com',
    'capitalone.com',
    'www.youtube.com',
    't.me',
    'bloomberg.com',
    'coccoc.com',
    'www.instagram.com',
    'fedex.com',
    'microsoft.com',
    'walmart.com',
    'discord.com',
    'twitch.tv',
    'target.com',
    'instagram.com',
    'wayfair.com',
    'bing.com',
    'quora.com',
    'lowes.com',
    'reddit.com',
    'yelp.com',
    'www.pinterest.com',
    'globo.com',
    'www.spotify.com',
    'ups.com',
    'ebay.com',
    'www.facebook.com',
    'accuweather.com',
    'yandex.ru',
    'pandora.com',
    'linkedin.com',
    'www.google.com',
    'wellsfargo.com',
    'www.wikipedia.org',
    'weather.com',
    'indeed.com',
    'vimeo.com',
    'www.aliexpress.com',
    'aliexpress.com',
    'yahoo.com',
    'imgur.com',
    'duckduckgo.com',
    'twitter.com',
    'chatgpt.com',
    'foxnews.com',
    'chase.com',
    'bestbuy.com',
    'facebook.com',
    'bbc.com',
    'sohu.com',
    'zoom.us',
    'www.tiktok.com',
    'canva.com',
    'www.twitch.tv',
    'businessinsider.com',
    'yahoo.co.jp',
    'bankofamerica.com',
    'msn.com',
    'soundcloud.com',
    'zhanqi.tv',
    'apple.com',
    'whatsapp.com',
    'speedtest.net',
    'www.xvideos.com',
    'onlyfans.com',
    'zillow.com',
    'adobe.com',
    'etsy.com',
    'washingtonpost.com',
    'pinterest.com',
    'office.com',
}


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}

def check_url(url, use_vpn=False):
    proxies = None
    if use_vpn:
        proxies = {
            'http': 'http://127.0.0.1:1081',
            'https': 'http://127.0.0.1:1081',
        }
    try:
        # verify=False matches the previous SSL context bypass
        # allow_redirects=True to handle cases where HEAD might be redirected
        r = requests.head(url, headers=HEADERS, proxies=proxies, timeout=3, verify=False, allow_redirects=True)
        return {'accessible': True, 'http_code': r.status_code, 'error': None}
    except requests.exceptions.HTTPError as e:
        return {'accessible': True, 'http_code': e.response.status_code, 'error': str(e)}
    except Exception as e:
        return {'accessible': False, 'http_code': 0, 'error': str(e)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # === API endpoint ===
        if parsed.path == '/api/check':
            params = parse_qs(parsed.query)
            url = params.get('url', [None])[0]
            use_vpn = params.get('use_vpn', ['false'])[0].lower() == 'true'

            if not url:
                self.send_response(400)
                self.end_headers()
                return

            try:
                parsed_url = urlparse(url)
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


            result = check_url(url, use_vpn=use_vpn)
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(body))
            self.send_cors()
            self.end_headers()
            self.wfile.write(body)

        # === Serve static index.html ===
        elif parsed.path in ('/', '/index.html'):
            try:
                with open('/var/www/monitor/index.html', 'rb') as f:
                    body = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8090), Handler)
    server.socket.setsockopt(1, 15, 1)  # SO_REUSEPORT
    print('Russia Monitor running on port 8090...')
    server.serve_forever()
