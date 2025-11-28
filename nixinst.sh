#!/usr/bin/env bash
set -euo pipefail

# NixOS Installation Script
# This script installs NixOS from a minimal ISO using the dotfiles flake
#
# Usage: ./nixinst.sh <machine-name> [disk] [repo-url]
# Example: ./nixinst.sh brian-laptop /dev/nvme0n1
#          ./nixinst.sh brian-laptop /dev/nvme0n1 https://github.com/user/dotfiles.git
#
# Note: If run from within the repository directory, it will use the existing
#       repository instead of cloning. Otherwise, it will clone from the URL.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root"
   exit 1
fi

# Check if we're in a live environment (optional check)
if [[ -d /iso ]]; then
    info "Detected live ISO environment"
elif [[ -f /etc/os-release ]] && grep -q "NixOS" /etc/os-release 2>/dev/null; then
    warning "This appears to be an installed NixOS system, not a live ISO"
    warning "This script is intended for installation from a minimal ISO"
    echo "Continue anyway? (yes/no)"
    read -r continue_anyway
    if [[ "$continue_anyway" != "yes" ]]; then
        exit 0
    fi
fi

# Parse arguments
MACHINE_NAME="${1:-}"
DISK="${2:-}"
REPO_URL="${3:-https://github.com/brian/dotfiles.git}"

if [[ -z "$MACHINE_NAME" ]]; then
    error "Usage: $0 <machine-name> [disk] [repo-url]"
    error "Available machines: brian-laptop, superheavy, docker, backup"
    exit 1
fi

info "Installing NixOS for machine: $MACHINE_NAME"
info "Repository: $REPO_URL"

# Step 1: Check network connectivity
info "Step 1: Checking network connectivity..."
if ping -c 1 8.8.8.8 &>/dev/null; then
    success "Network connectivity confirmed"
else
    warning "No network connectivity detected"
    echo ""
    echo "Would you like to configure WiFi? (y/n)"
    read -r configure_wifi
    
    if [[ "$configure_wifi" == "y" || "$configure_wifi" == "Y" ]]; then
        info "Configuring WiFi..."
        
        # Prefer nmtui (NetworkManager TUI) if available - it's easier to use
        if command -v nmtui &>/dev/null; then
            info "Starting NetworkManager TUI..."
            info "Please connect to WiFi using the TUI interface, then press Enter here..."
            nmtui
            sleep 3
            
            if ping -c 1 8.8.8.8 &>/dev/null; then
                success "WiFi connected successfully"
            else
                warning "Connection may still be establishing. Testing again..."
                sleep 5
                if ping -c 1 8.8.8.8 &>/dev/null; then
                    success "WiFi connected successfully"
                else
                    error "Failed to connect. Please try again or configure manually."
                    exit 1
                fi
            fi
        elif command -v wpa_supplicant &>/dev/null; then
            # Fallback to wpa_supplicant
            info "Using wpa_supplicant for WiFi configuration..."
            echo "Enter WiFi SSID:"
            read -r wifi_ssid
            echo "Enter WiFi password:"
            read -rs wifi_password
            
            # Create wpa_supplicant config
            WPA_CONF=$(mktemp)
            cat > "$WPA_CONF" <<EOF
network={
    ssid="$wifi_ssid"
    psk="$wifi_password"
}
EOF
            
            # Find wireless interface
            WIFI_INTERFACE=$(ip link show | grep -E "^[0-9]+: w" | head -1 | cut -d: -f2 | awk '{print $1}')
            
            if [[ -n "$WIFI_INTERFACE" ]]; then
                info "Connecting to $wifi_ssid on $WIFI_INTERFACE..."
                wpa_supplicant -B -i "$WIFI_INTERFACE" -c "$WPA_CONF"
                sleep 5
                
                # Try to get IP via DHCP
                dhclient "$WIFI_INTERFACE" || true
                
                # Wait a bit for connection
                sleep 3
                
                if ping -c 1 8.8.8.8 &>/dev/null; then
                    success "WiFi connected successfully"
                else
                    error "Failed to connect to WiFi. Please configure manually."
                    exit 1
                fi
            else
                error "No wireless interface found"
                exit 1
            fi
            
            rm -f "$WPA_CONF"
        else
            warning "No WiFi configuration tools available (nmtui or wpa_supplicant)."
            warning "Please configure network manually using:"
            warning "  - nmtui (if NetworkManager is available)"
            warning "  - wpa_supplicant (if installed)"
            warning "  - Or use ethernet connection"
            echo "Press Enter when network is configured..."
            read -r
            
            if ! ping -c 1 8.8.8.8 &>/dev/null; then
                error "Network connectivity still not available. Exiting."
                exit 1
            fi
        fi
    else
        error "Network connectivity required. Please configure network manually and re-run."
        exit 1
    fi
fi

# Step 2: Install git and other required tools
info "Step 2: Installing required tools..."

# On minimal ISO, we might need to use nix-shell or nix-env
if ! command -v git &>/dev/null; then
    info "Installing git..."
    if command -v nix-env &>/dev/null; then
        nix-env -iA nixpkgs.git
    else
        # Try using nix-shell as fallback
        nix-shell -p git --run "git --version" || {
            error "Could not install git. Please ensure Nix is properly configured."
            exit 1
        }
    fi
fi

if ! command -v parted &>/dev/null; then
    info "Installing parted..."
    if command -v nix-env &>/dev/null; then
        nix-env -iA nixpkgs.parted
    else
        nix-shell -p parted --run "parted --version" || {
            error "Could not install parted. Please ensure Nix is properly configured."
            exit 1
        }
    fi
fi

# Step 3: Prepare disks
info "Step 3: Preparing disks..."

if [[ -z "$DISK" ]]; then
    info "Available disks:"
    lsblk -d -o NAME,SIZE,MODEL
    echo ""
    echo "Enter the disk to install to (e.g., /dev/nvme0n1 or /dev/sda):"
    read -r DISK
fi

if [[ ! -b "$DISK" ]]; then
    error "Invalid disk: $DISK"
    exit 1
fi

warning "WARNING: This will DESTROY all data on $DISK"
echo "Are you sure you want to continue? (yes/no)"
read -r confirm

if [[ "$confirm" != "yes" ]]; then
    info "Installation cancelled"
    exit 0
fi

info "Partitioning $DISK..."

# Unmount any existing partitions
umount -R /mnt 2>/dev/null || true
swapoff -a 2>/dev/null || true

# Create partition table (GPT)
parted "$DISK" -- mklabel gpt

# Create boot partition (EFI, 2048MB / 2GB)
EFI_SIZE_MIB=2049
parted "$DISK" -- mkpart ESP fat32 1MiB ${EFI_SIZE_MIB}MiB
parted "$DISK" -- set 1 esp on

# Create root partition (rest of disk)
parted "$DISK" -- mkpart primary ext4 ${EFI_SIZE_MIB}MiB 100%

# Wait for partitions to be available
sleep 2

# Format partitions
info "Formatting partitions..."

# Find partition names (handle both /dev/sda and /dev/nvme0n1 style)
if [[ "$DISK" == *"nvme"* ]]; then
    BOOT_PART="${DISK}p1"
    ROOT_PART="${DISK}p2"
else
    BOOT_PART="${DISK}1"
    ROOT_PART="${DISK}2"
fi

# Format boot partition (FAT32)
mkfs.fat -F 32 -n BOOT "$BOOT_PART"

# Format root partition (ext4)
mkfs.ext4 -L nixos "$ROOT_PART"

# Mount filesystems
info "Mounting filesystems..."
mount "$ROOT_PART" /mnt
mkdir -p /mnt/boot
mount "$BOOT_PART" /mnt/boot

success "Disks prepared and mounted"

# Step 4: Copy repository and install
info "Step 4: Setting up repository and installing NixOS..."

# Check if repository exists in current directory
REPO_SOURCE=""
if [[ -d "$(pwd)/.git" ]] && [[ -f "$(pwd)/flake.nix" ]]; then
    info "Found repository in current directory: $(pwd)"
    REPO_SOURCE="$(pwd)"
elif [[ -d "$(pwd)/dotfiles/.git" ]] && [[ -f "$(pwd)/dotfiles/flake.nix" ]]; then
    info "Found repository in dotfiles subdirectory"
    REPO_SOURCE="$(pwd)/dotfiles"
fi

# Copy or clone repository
if [[ -d /mnt/etc/nixos ]]; then
    warning "/mnt/etc/nixos already exists, removing..."
    rm -rf /mnt/etc/nixos
fi

mkdir -p /mnt/etc/nixos

if [[ -n "$REPO_SOURCE" ]]; then
    info "Copying repository from $REPO_SOURCE to /mnt/etc/nixos..."
    cp -r "$REPO_SOURCE"/* /mnt/etc/nixos/
    cp -r "$REPO_SOURCE"/.git /mnt/etc/nixos/ 2>/dev/null || true
    success "Repository copied successfully"
else
    warning "Repository not found in current directory"
    info "Cloning repository from $REPO_URL..."
    git clone "$REPO_URL" /mnt/etc/nixos
fi

# Verify machine name exists
if [[ ! -d "/mnt/etc/nixos/machines/$MACHINE_NAME" ]]; then
    error "Machine '$MACHINE_NAME' not found in repository"
    error "Available machines:"
    ls -1 /mnt/etc/nixos/machines/ 2>/dev/null || echo "  (none found)"
    exit 1
fi

# Generate hardware configuration if it doesn't exist or is outdated
info "Generating hardware configuration..."
nixos-generate-config --root /mnt --no-filesystems

# Update hardware-configuration.nix with actual partition UUIDs
info "Updating hardware configuration with partition UUIDs..."

BOOT_UUID=$(blkid -s UUID -o value "$BOOT_PART")
ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")

HARDWARE_CONFIG="/mnt/etc/nixos/machines/$MACHINE_NAME/hardware-configuration.nix"

if [[ -f "$HARDWARE_CONFIG" ]]; then
    info "Updating existing hardware-configuration.nix with partition UUIDs..."
    # Update root filesystem UUID (for /)
    sed -i "s|fileSystems.\"/\" =|fileSystems.\"/\" =|" "$HARDWARE_CONFIG"
    sed -i "/fileSystems.\"\/\" =/,/};/s|device = \"/dev/disk/by-uuid/[^\"]*\";|device = \"/dev/disk/by-uuid/$ROOT_UUID\";|" "$HARDWARE_CONFIG"
    # Update boot filesystem UUID (for /boot)
    sed -i "/fileSystems.\"\/boot\" =/,/};/s|device = \"/dev/disk/by-uuid/[^\"]*\";|device = \"/dev/disk/by-uuid/$BOOT_UUID\";|" "$HARDWARE_CONFIG"
else
    warning "hardware-configuration.nix not found, creating from generated config..."
    # Copy generated config to machine directory
    if [[ -f /mnt/etc/nixos/hardware-configuration.nix ]]; then
        cp /mnt/etc/nixos/hardware-configuration.nix "$HARDWARE_CONFIG"
        # Update root filesystem UUID
        sed -i "/fileSystems.\"\/\" =/,/};/s|device = \"/dev/disk/by-uuid/[^\"]*\";|device = \"/dev/disk/by-uuid/$ROOT_UUID\";|" "$HARDWARE_CONFIG"
        # Update boot filesystem UUID
        sed -i "/fileSystems.\"\/boot\" =/,/};/s|device = \"/dev/disk/by-uuid/[^\"]*\";|device = \"/dev/disk/by-uuid/$BOOT_UUID\";|" "$HARDWARE_CONFIG"
    else
        error "Could not generate hardware configuration"
        exit 1
    fi
fi

# Install NixOS
info "Installing NixOS with flake configuration..."
cd /mnt/etc/nixos

# Verify flake can be evaluated
info "Verifying flake configuration..."
if ! nix flake check ".#$MACHINE_NAME" 2>/dev/null; then
    warning "Flake check had warnings, but continuing..."
fi

# Build and install the system
info "Building and installing NixOS (this may take a while)..."
nixos-install --flake ".#$MACHINE_NAME" --no-root-password

success "NixOS installation completed successfully!"
info ""

# Prompt to set root password
echo ""
info "Would you like to set the root password now? (y/n)"
read -r set_password

if [[ "$set_password" == "y" || "$set_password" == "Y" ]]; then
    info "Setting root password..."
    # Use chroot to set password in the installed system
    chroot /mnt passwd root
    if [[ $? -eq 0 ]]; then
        success "Root password set successfully"
    else
        warning "Password setting may have failed. You can set it manually after reboot with: passwd root"
    fi
else
    warning "Skipping root password setup. Remember to set it after reboot with: passwd root"
fi

info ""
info "Next steps:"
info "1. Reboot: sudo reboot"
info "2. After reboot, you can manage your system with:"
info "   sudo nixos-rebuild switch --flake /etc/nixos#$MACHINE_NAME"
info ""
success "Installation complete! You can now reboot your system."

