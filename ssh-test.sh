#!/usr/bin/env bash
# SSH connectivity diagnostic script

echo "=== SSH Configuration Diagnostic ==="
echo ""

# Show local SSH keys
echo "1. Local SSH keys:"
if [[ -f ~/.ssh/id_ed25519.pub ]]; then
    echo "   Found: ~/.ssh/id_ed25519.pub"
    cat ~/.ssh/id_ed25519.pub
else
    echo "   ERROR: ~/.ssh/id_ed25519.pub not found!"
fi
echo ""

# Show authorized_keys on this machine
echo "2. Authorized keys on this machine:"
if [[ -f ~/.ssh/authorized_keys ]]; then
    echo "   ~/.ssh/authorized_keys exists ($(wc -l < ~/.ssh/authorized_keys) keys)"
    cat ~/.ssh/authorized_keys
else
    echo "   ERROR: ~/.ssh/authorized_keys not found!"
fi
echo ""

# Show SSH config
echo "3. SSH Server Status:"
systemctl status ssh --no-pager || systemctl status sshd --no-pager || echo "   SSH service status unknown"
echo ""

# Show SSH known_hosts
echo "4. System SSH known_hosts:"
if [[ -f /etc/ssh/ssh_known_hosts ]]; then
    echo "   /etc/ssh/ssh_known_hosts exists ($(wc -l < /etc/ssh/ssh_known_hosts) entries)"
    cat /etc/ssh/ssh_known_hosts
else
    echo "   ERROR: /etc/ssh/ssh_known_hosts not found!"
fi
echo ""

# Test SSH with verbose mode
echo "5. Test SSH connection (example usage):"
echo "   ssh -vvv brian@<remote-machine>"
echo "   (Replace <remote-machine> with superheavy, docker, backup, or brian-laptop)"
echo ""

# Show hostname
echo "6. Current machine:"
echo "   hostname: $(hostname)"
echo "   FQDN might be: $(hostname -f 2>/dev/null || echo 'unknown')"
