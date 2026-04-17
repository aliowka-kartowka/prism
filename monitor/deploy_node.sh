#!/bin/bash

# FreeNet Node Deployment Script (VLESS + Reality)
# Works on Ubuntu 20.04/22.04/24.04

set -e

echo "🚀 Starting FreeNet Node Deployment..."

# 1. Update system and install dependencies
sudo apt-get update && sudo apt-get install -y curl jq openssl uuid-runtime

# 2. Install Docker if not present
if ! [ -x "$(command -v docker)" ]; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

# 3. Create workspace
mkdir -p ~/freenet-node && cd ~/freenet-node

# 4. Generate keys for Reality
UUID=$(uuidgen)
PRIV_KEY=$(docker run --rm teddysun/xray xray genkey)
PUB_KEY=$(echo $PRIV_KEY | docker run -i --rm teddysun/xray xray pubkey)
SHORT_ID=$(openssl rand -hex 8)

echo "🔑 Generated credentials:"
echo "UUID: $UUID"
echo "Public Key: $PUB_KEY"
echo "Short ID: $SHORT_ID"

# 5. Create Xray config
cat <<EOF > config.json
{
    "log": { "loglevel": "info" },
    "inbounds": [{
        "port": 443,
        "protocol": "vless",
        "settings": {
            "clients": [{ "id": "$UUID", "flow": "xtls-rprx-vision" }],
            "decryption": "none"
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": false,
                "dest": "google.com:443",
                "xver": 0,
                "serverNames": ["google.com", "www.google.com"],
                "privateKey": "$PRIV_KEY",
                "shortIds": ["$SHORT_ID"]
            }
        }
    }],
    "outbounds": [{ "protocol": "freedom" }]
}
EOF

# 6. Run Xray in Docker
docker rm -f xray || true
docker run -d --name xray \
    --restart always \
    --network host \
    -v ~/freenet-node/config.json:/etc/xray/config.json \
    teddysun/xray

IP=$(curl -s https://ifconfig.me)

echo "✅ NODE DEPLOYED SUCCESSFULLY!"
echo "--------------------------------------------------"
echo "Your connection link (VLESS + Reality):"
echo "vless://$UUID@$IP:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=google.com&fp=chrome&pbk=$PUB_KEY&sid=$SHORT_ID#FreeNet-NewNode"
echo "--------------------------------------------------"
echo "Add this link to your Telegram Bot / Admin Panel."
