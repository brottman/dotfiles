#!/usr/bin/env bash
# Debug SSH configuration

echo "=== SSH Configuration Debug ==="
echo ""

echo "1. Check if ~/.ssh/authorized_keys exists:"
if [[ -f ~/.ssh/authorized_keys ]]; then
    echo "   ✓ File exists"
    echo "   Permissions: $(stat -c '%a' ~/.ssh/authorized_keys)"
    echo "   Owner: $(stat -c '%U:%G' ~/.ssh/authorized_keys)"
    echo "   Content ($(wc -l < ~/.ssh/authorized_keys) lines):"
    cat ~/.ssh/authorized_keys
else
    echo "   ✗ File NOT FOUND!"
fi
echo ""

echo "2. Check /etc/ssh/ssh_known_hosts:"
if [[ -f /etc/ssh/ssh_known_hosts ]]; then
    echo "   ✓ File exists"
    echo "   Content ($(wc -l < /etc/ssh/ssh_known_hosts) lines):"
    cat /etc/ssh/ssh_known_hosts
else
    echo "   ✗ File NOT FOUND!"
fi
echo ""

echo "3. SSH Service Status:"
sudo systemctl status sshd --no-pager 2>/dev/null || echo "   Could not check status"
echo ""

echo "4. SSH config relevant settings:"
sudo sshd -T 2>/dev/null | grep -E "pubkeyauthentication|passwordauthentication|permituserenvironment" || echo "   Could not get sshd config"
echo ""

echo "5. Check brian user home directory:"
ls -lah ~
echo ""

echo "6. Check .ssh directory permissions:"
if [[ -d ~/.ssh ]]; then
    ls -lah ~/.ssh/
else
    echo "   ~/.ssh directory does not exist!"
fi
echo ""

echo "7. Recent SSH logs:"
sudo journalctl -u sshd -n 20 --no-pager || echo "   Could not get logs"

