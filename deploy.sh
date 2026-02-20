#!/bin/bash
# Deploy doc-qa-platform on a fresh Ubuntu VPS (ARM or x86)
# Usage: curl -sSL <raw-url> | bash
# Or:    ssh user@vps 'bash -s' < deploy.sh

set -euo pipefail

echo "=== doc-qa-platform deployment ==="

# 1. Install Docker if not present
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in for group changes."
fi

# 2. Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 3. Clone repo
APP_DIR="$HOME/doc-qa-platform"
if [ -d "$APP_DIR" ]; then
    echo "Updating existing installation..."
    cd "$APP_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/<your-username>/doc-qa-platform.git "$APP_DIR"
    cd "$APP_DIR"
fi

# 4. Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> IMPORTANT: Edit .env and set your GEMINI_API_KEY <<<"
    echo "    nano $APP_DIR/.env"
    echo ""
    echo "Then re-run this script."
    exit 0
fi

# 5. Open firewall ports
if command -v ufw &>/dev/null; then
    echo "Configuring firewall..."
    sudo ufw allow 80/tcp
    sudo ufw allow 22/tcp
    sudo ufw --force enable
fi

# 6. Build and start
echo "Building and starting services..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "=== Deployment complete ==="
echo "API: http://$(curl -s ifconfig.me)"
echo "Health: http://$(curl -s ifconfig.me)/health"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f backend    # View logs"
echo "  docker compose ps                 # Check status"
echo "  docker compose down               # Stop"
echo "  docker compose up -d --build      # Rebuild + restart"
