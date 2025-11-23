#!/usr/bin/env bash
# Script to fix corrupted Tailscale state on superheavy machine
# This script should be run on the superheavy machine

set -euo pipefail

echo "Fixing Tailscale state corruption..."

# Stop the tailscaled service
echo "Stopping tailscaled service..."
sudo systemctl stop tailscaled.service || true

# Backup the current state directory (just in case)
STATE_DIR="/var/lib/tailscale"
if [ -d "$STATE_DIR" ]; then
    BACKUP_DIR="/var/lib/tailscale.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up state directory to $BACKUP_DIR..."
    sudo mv "$STATE_DIR" "$BACKUP_DIR"
    echo "Backup created at $BACKUP_DIR"
fi

# Recreate the state directory with proper permissions
echo "Creating fresh state directory..."
sudo mkdir -p "$STATE_DIR"
sudo chown tailscale:tailscale "$STATE_DIR"
sudo chmod 700 "$STATE_DIR"

# Start the tailscaled service
echo "Starting tailscaled service..."
sudo systemctl start tailscaled.service

# Wait a moment and check status
sleep 2
echo ""
echo "Checking tailscaled status..."
sudo systemctl status tailscaled.service --no-pager || true

echo ""
echo "Done! Tailscale should now start properly."
echo "You may need to re-authenticate with: sudo tailscale up"

