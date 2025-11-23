#!/usr/bin/env bash
# Generate SSH keys for the brian user on each machine if they don't exist

set -e

echo "Generating SSH keys for user 'brian'..."

# Ensure .ssh directory exists
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Generate ed25519 key if it doesn't exist
if [[ ! -f ~/.ssh/id_ed25519 ]]; then
    echo "Generating new ed25519 SSH key..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "brian@$(hostname)"
    echo "✓ Generated ~/.ssh/id_ed25519"
else
    echo "✓ ~/.ssh/id_ed25519 already exists"
fi

# Show the public key
echo ""
echo "Public key for this machine:"
echo "========================================"
cat ~/.ssh/id_ed25519.pub
echo "========================================"
echo ""
echo "This key should be added to the 'authorizedKeys' of each machine's configuration."
