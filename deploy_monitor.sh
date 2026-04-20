#!/bin/bash
# Moscow Node (API + Backup Monitor)
MOSCOW_IP="94.159.117.222"
MOSCOW_DIR="/home/aliowka/workspace/monitor"
MOSCOW_USER="aliowka"

# Hetzner Node (Main Web Front)
HETZNER_ALIAS="vpn"
HETZNER_DIR="/var/www/monitor"

echo "🚀 Deploying Monitor Branding to components..."

# 1. Sync to Moscow (Backend API + Subdomain)
echo "📡 Deploying to Moscow node (API)..."
rsync -avz --exclude '.git' ./monitor/ $MOSCOW_USER@$MOSCOW_IP:$MOSCOW_DIR/
ssh $MOSCOW_USER@$MOSCOW_IP "pkill -u $MOSCOW_USER -f server.py || true; cd $MOSCOW_DIR && nohup python3 server.py > server.log 2>&1 &"

# 2. Sync to Hetzner (Main Domain freenet.monster)
echo "📡 Deploying to Hetzner node (Web)..."
rsync -avz --exclude '.git' ./monitor/ $HETZNER_ALIAS:$HETZNER_DIR/
ssh $HETZNER_ALIAS "chown -R www-data:www-data $HETZNER_DIR"

echo "✅ Deployment complete! Branding updates should be visible at https://freenet.monster/"
