import re

with open('allowed_list.txt', 'r') as f:
    domains = [d.strip() for d in f.readlines() if d.strip()]

domains_list = "ALLOWED_DOMAINS = {\n"
for d in set(domains):
    domains_list += f"    '{d}',\n"
domains_list += "}\n"

with open('russia_monitor/server.py', 'r') as f:
    content = f.read()

# insert ALLOWED_DOMAINS after urllib3
content = content.replace("urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)", "urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\n\n" + domains_list)

# insert check
check_logic = """            if not url:
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
"""

content = content.replace("""            if not url:
                self.send_response(400)
                self.end_headers()
                return""", check_logic)

with open('russia_monitor/server.py', 'w') as f:
    f.write(content)
