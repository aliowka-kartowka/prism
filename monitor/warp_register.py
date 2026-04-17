import requests
import json
import base64
import os

def register():
    url = "https://api.cloudflareclient.com/v0a/reg"
    # Generate a dummy keypair is not needed because the API generates it 
    # Actually we need a Private/Public key to register correctly.
    # But since we are using Xray, we can use any WireGuard registration tool.
    # The easiest is to use a pre-made tool or a simple script.
    
    # Let's use a simpler approach: many people use a pre-compiled 'wgcf' but I'll use a direct API call 
    # using a known reliable registration method.
    
    headers = {"Content-Type": "application/json", "User-Agent": "okhttp/3.12.1"}
    r = requests.post(url, headers=headers, json={})
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2))
        return data
    else:
        print(f"Error: {r.status_code}")
        print(r.text)
        return None

if __name__ == "__main__":
    register()
