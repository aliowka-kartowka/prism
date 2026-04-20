#!/bin/bash
TARGET_IP="94.159.117.222"
TARGET_DIR="/root/monitor"

echo "🚀 Deploying Monitor to $TARGET_IP..."

# Sync files
# We sync the monitor/ directory content to the target directory
rsync -avz --exclude '.git' ./monitor/ root@$TARGET_IP:$TARGET_DIR/

# Restart server
# We kill the old server.py process and start a new one in the background
echo "🔄 Restarting Monitor service..."
ssh root@$TARGET_IP "pkill -f server.py || true; cd $TARGET_DIR && nohup python3 server.py > server.log 2>&1 &"

echo "✅ Deployment complete!"
