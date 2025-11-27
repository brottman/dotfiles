#!/usr/bin/env bash
# System health check script
# Checks services, disk space, network connectivity, and Tailscale status

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall health
HEALTHY=true
WARNINGS=0
ERRORS=0

# Machine hostnames (can be overridden via environment or arguments)
MACHINES="${MACHINES:-brian-laptop superheavy backup docker}"
CURRENT_HOST=$(hostname)

# Disk space threshold (percentage)
DISK_WARN_THRESHOLD=80
DISK_CRITICAL_THRESHOLD=90

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        WARNINGS=$((WARNINGS + 1))
        HEALTHY=false
    else
        echo -e "${RED}✗${NC} $message"
        ERRORS=$((ERRORS + 1))
        HEALTHY=false
    fi
}

# Function to check if a service is running
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        print_status "OK" "Service '$service' is running"
        return 0
    elif systemctl is-enabled --quiet "$service" 2>/dev/null; then
        print_status "ERROR" "Service '$service' is enabled but not running"
        return 1
    else
        # Service might not be configured on this machine, skip silently
        return 2
    fi
}

echo "=========================================="
echo "System Health Check"
echo "Host: $CURRENT_HOST"
echo "Date: $(date)"
echo "=========================================="
echo ""

# ============================================
# 1. Check Services
# ============================================
echo "1. Checking Services"
echo "--------------------"

# Core services that should be on all machines
CORE_SERVICES=(
    "sshd"
    "docker"
    "tailscaled"
    "NetworkManager"
)

# Check core services
for service in "${CORE_SERVICES[@]}"; do
    check_service "$service" || true
done

# Machine-specific services
case "$CURRENT_HOST" in
    superheavy)
        check_service "postfix" || true
        check_service "samba" || true
        check_service "cups" || true
        ;;
    brian-laptop)
        check_service "sddm" || true
        check_service "pipewire" || true
        check_service "bluetooth" || true
        check_service "nginx" || true
        check_service "ollama" || true
        ;;
esac

# Check all enabled services for failures
echo ""
echo "Checking for failed services..."
FAILED_SERVICES=$(systemctl list-units --state=failed --no-legend 2>/dev/null | awk '{print $1}' || true)
if [ -z "$FAILED_SERVICES" ]; then
    print_status "OK" "No failed services"
else
    while IFS= read -r service; do
        [ -n "$service" ] && print_status "ERROR" "Failed service: $service"
    done <<< "$FAILED_SERVICES"
fi

echo ""

# ============================================
# 2. Check Disk Space
# ============================================
echo "2. Checking Disk Space"
echo "----------------------"

# Get disk usage, excluding tmpfs, devtmpfs, and other virtual filesystems
df -h 2>/dev/null | (grep -E '^/dev|^/run/media' || true) | while read -r line; do
    filesystem=$(echo "$line" | awk '{print $1}')
    size=$(echo "$line" | awk '{print $2}')
    used=$(echo "$line" | awk '{print $3}')
    avail=$(echo "$line" | awk '{print $4}')
    use_percent_str=$(echo "$line" | awk '{print $5}' | sed 's/%//')
    mount=$(echo "$line" | awk '{print $6}')
    
    if [ -z "$use_percent_str" ] || [ "$use_percent_str" = "-" ]; then
        continue
    fi
    
    # Convert to integer for comparison
    use_percent=${use_percent_str%.*}
    
    if [ "$use_percent" -ge "$DISK_CRITICAL_THRESHOLD" ]; then
        print_status "ERROR" "Disk $filesystem ($mount): ${use_percent}% used (CRITICAL: >=${DISK_CRITICAL_THRESHOLD}%)"
    elif [ "$use_percent" -ge "$DISK_WARN_THRESHOLD" ]; then
        print_status "WARN" "Disk $filesystem ($mount): ${use_percent}% used (WARNING: >=${DISK_WARN_THRESHOLD}%)"
    else
        print_status "OK" "Disk $filesystem ($mount): ${use_percent}% used ($used/$size used, $avail available)"
    fi
done

echo ""

# ============================================
# 3. Check Network Connectivity
# ============================================
echo "3. Checking Network Connectivity"
echo "--------------------------------"

# Check internet connectivity
if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    print_status "OK" "Internet connectivity (8.8.8.8)"
else
    print_status "ERROR" "No internet connectivity (8.8.8.8)"
fi

# Check DNS
if ping -c 1 -W 2 google.com &>/dev/null; then
    print_status "OK" "DNS resolution (google.com)"
else
    print_status "ERROR" "DNS resolution failed (google.com)"
fi

# Check connectivity to other machines
echo ""
echo "Checking connectivity to other machines..."
for machine in $MACHINES; do
    if [ "$machine" = "$CURRENT_HOST" ]; then
        continue
    fi
    
    # Try to resolve hostname
    if getent hosts "$machine" &>/dev/null || ping -c 1 -W 2 "$machine" &>/dev/null; then
        print_status "OK" "Can reach $machine"
    else
        print_status "WARN" "Cannot reach $machine (may be offline or not on network)"
    fi
done

echo ""

# ============================================
# 4. Check Tailscale Connectivity
# ============================================
echo "4. Checking Tailscale"
echo "--------------------"

# Check if tailscale is installed and running
if ! command -v tailscale &> /dev/null; then
    print_status "ERROR" "Tailscale command not found"
else
    # Check tailscaled service
    if systemctl is-active --quiet tailscaled 2>/dev/null; then
        print_status "OK" "tailscaled service is running"
        
        # Check Tailscale status
        TS_STATUS=$(tailscale status 2>/dev/null || echo "")
        if [ -n "$TS_STATUS" ]; then
            # Check if we're logged in (status will show our hostname)
            if echo "$TS_STATUS" | grep -q "$CURRENT_HOST" 2>/dev/null; then
                print_status "OK" "Tailscale is connected"
                
                # Get Tailscale IP
                TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
                if [ -n "$TS_IP" ]; then
                    print_status "OK" "Tailscale IP: $TS_IP"
                else
                    print_status "WARN" "Could not determine Tailscale IP"
                fi
                
                # Check connectivity to other machines via Tailscale
                echo ""
                echo "Checking Tailscale connectivity to other machines..."
                for machine in $MACHINES; do
                    if [ "$machine" = "$CURRENT_HOST" ]; then
                        continue
                    fi
                    
                    # Check if machine appears in Tailscale status
                    if echo "$TS_STATUS" | grep -q "$machine" 2>/dev/null; then
                        # Get machine's Tailscale IP
                        MACHINE_IP=$(tailscale ip "$machine" 2>/dev/null || echo "")
                        if [ -n "$MACHINE_IP" ]; then
                            # Try to ping the machine via its Tailscale IP
                            if ping -c 1 -W 2 "$MACHINE_IP" &>/dev/null 2>&1; then
                                print_status "OK" "Can reach $machine via Tailscale ($MACHINE_IP)"
                            else
                                print_status "WARN" "$machine is in Tailscale but not responding ($MACHINE_IP)"
                            fi
                        else
                            print_status "WARN" "$machine is in Tailscale but IP unknown"
                        fi
                    else
                        print_status "WARN" "$machine not found in Tailscale network (may be offline)"
                    fi
                done
            else
                print_status "ERROR" "Tailscale is not connected (may need: sudo tailscale up)"
            fi
        else
            print_status "ERROR" "Cannot get Tailscale status (may need authentication)"
        fi
    else
        print_status "ERROR" "tailscaled service is not running"
    fi
fi

echo ""

# ============================================
# Summary
# ============================================
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}✓ System is healthy${NC}"
    exit 0
else
    echo -e "${RED}✗ System has issues${NC}"
    exit 1
fi

