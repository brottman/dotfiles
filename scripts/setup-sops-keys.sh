#!/usr/bin/env bash
# Generate age keys for sops-nix
# Run this script to generate keys for each machine

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEYS_DIR="$REPO_ROOT/secrets/keys"

echo "SOPS Age Key Generator"
echo "======================"
echo ""

# Check if age is available
if ! command -v age &> /dev/null; then
    echo "Error: 'age' command not found."
    echo "Install it with: nix profile install nixpkgs#age"
    echo "Or enter the dev shell: nix develop"
    exit 1
fi

# Create keys directory if it doesn't exist
mkdir -p "$KEYS_DIR"

# List of machines
MACHINES=("superheavy" "brian-laptop" "docker" "backup")

echo "This script will generate age keys for the following machines:"
for machine in "${MACHINES[@]}"; do
    echo "  - $machine"
done
echo ""

# Ask for confirmation
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Generating keys..."

# Generate keys for each machine
for machine in "${MACHINES[@]}"; do
    KEY_FILE="$KEYS_DIR/$machine.age"
    
    if [[ -f "$KEY_FILE" ]]; then
        echo "⚠️  Key for $machine already exists: $KEY_FILE"
        read -p "  Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "  Skipping $machine"
            continue
        fi
    fi
    
    echo "Generating key for $machine..."
    age-keygen -o "$KEY_FILE"
    
    # Extract and display public key
    PUBLIC_KEY=$(grep "public key:" "$KEY_FILE" | cut -d: -f2 | tr -d ' ')
    echo "  ✓ Generated: $KEY_FILE"
    echo "  Public key: $PUBLIC_KEY"
    echo ""
done

echo "✅ Key generation complete!"
echo ""
echo "Next steps:"
echo "1. Copy the public keys above to secrets/.sops.yaml"
echo "2. Copy each private key to the corresponding machine:"
echo "   sudo mkdir -p /etc/sops/age"
echo "   sudo cp secrets/keys/MACHINE.age /etc/sops/age/keys.txt"
echo "   sudo chmod 600 /etc/sops/age/keys.txt"
echo ""
echo "⚠️  IMPORTANT: Private keys are in .gitignore and should NEVER be committed!"

