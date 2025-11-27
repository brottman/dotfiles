#!/usr/bin/env bash
# Script to manage NixOS configurations across multiple machines

set -e

MACHINES=("brian-laptop" "superheavy" "docker" "backup")
FLAKE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

get_current_machine() {
    local hostname
    hostname=$(hostname)
    
    # Match hostname to a known machine
    for machine in "${MACHINES[@]}"; do
        if [[ "$hostname" == "$machine" ]]; then
            echo "$machine"
            return 0
        fi
    done
    
    # No match found
    return 1
}

print_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
  switch [MACHINE]      Switch to configuration for specified machine
  build [MACHINE]       Build configuration for specified machine
  dry-run [MACHINE]     Perform a dry run of switching configuration
  boot [MACHINE]        Apply configuration on next boot instead of immediately
  rebuild-all           Build all machine configurations
  update                Update all flake inputs
  update-nixpkgs        Update nixpkgs only
  pull                  Git pull latest changes and rerun the script
  list-machines         List all available machines
  status [MACHINE]      Show status of a machine
  health                Run system health check
  gc                    Garbage collect old generations
  create-vm             Create a new virtual machine (interactive or with flags)

Options:
  -v, --verbose         Show verbose output during build
  --show-trace          Show full stack traces for errors

Examples:
  $0 switch brian-laptop
  $0 boot brian-laptop
  $0 build superheavy --verbose
  $0 rebuild-all --show-trace
  $0 update
  $0 pull
  $0 list-machines
  $0 create-vm
  $0 create-vm --name myvm --os nixos --memory 8G --cpus 4 --disk 40G

EOF
}

check_machine() {
    if [[ ! " ${MACHINES[@]} " =~ " ${1} " ]]; then
        echo "Error: Unknown machine '$1'"
        echo "Available machines: ${MACHINES[*]}"
        exit 1
    fi
}

cmd_switch() {
    local machine="${1:-}"
    local verbose_flags=""
    
    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                verbose_flags="--verbose"
                shift
                ;;
            --show-trace)
                verbose_flags="$verbose_flags --show-trace"
                shift
                ;;
            *)
                machine="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "$machine" ]]; then
        machine=$(get_current_machine)
        if [[ -z "$machine" ]]; then
            echo "Error: Machine name required and could not detect from hostname"
            print_usage
            exit 1
        fi
        echo "Detected machine from hostname: $machine"
    fi
    
    check_machine "$machine"
    echo "Switching to $machine configuration..."
    cd "$FLAKE_PATH"
    # shellcheck disable=SC2086
    sudo nixos-rebuild switch --flake ".#$machine" $verbose_flags
}

cmd_boot() {
    local machine="${1:-}"
    local verbose_flags=""
    
    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                verbose_flags="--verbose"
                shift
                ;;
            --show-trace)
                verbose_flags="$verbose_flags --show-trace"
                shift
                ;;
            *)
                machine="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "$machine" ]]; then
        machine=$(get_current_machine)
        if [[ -z "$machine" ]]; then
            echo "Error: Machine name required and could not detect from hostname"
            print_usage
            exit 1
        fi
        echo "Detected machine from hostname: $machine"
    fi
    
    check_machine "$machine"
    echo "Building $machine configuration for next boot..."
    cd "$FLAKE_PATH"
    # shellcheck disable=SC2086
    sudo nixos-rebuild boot --flake ".#$machine" $verbose_flags
}

cmd_build() {
    local machine="${1:-}"
    local verbose_flags=""
    
    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                verbose_flags="--verbose"
                shift
                ;;
            --show-trace)
                verbose_flags="$verbose_flags --show-trace"
                shift
                ;;
            *)
                machine="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "$machine" ]]; then
        machine=$(get_current_machine)
        if [[ -z "$machine" ]]; then
            echo "Error: Machine name required and could not detect from hostname"
            print_usage
            exit 1
        fi
        echo "Detected machine from hostname: $machine"
    fi
    
    check_machine "$machine"
    echo "Building $machine configuration..."
    cd "$FLAKE_PATH"
    # shellcheck disable=SC2086
    nix build ".#nixosConfigurations.$machine.config.system.build.toplevel" --extra-experimental-features nix-command --extra-experimental-features flakes -o result $verbose_flags
}

cmd_dry_run() {
    local machine="${1:-}"
    if [[ -z "$machine" ]]; then
        machine=$(get_current_machine)
        if [[ -z "$machine" ]]; then
            echo "Error: Machine name required and could not detect from hostname"
            print_usage
            exit 1
        fi
        echo "Detected machine from hostname: $machine"
    fi
    
    check_machine "$machine"
    echo "Performing dry run for $machine..."
    cd "$FLAKE_PATH"
    sudo nixos-rebuild dry-run --flake ".#$machine"
}

cmd_update() {
    echo "Updating all flake inputs..."
    cd "$FLAKE_PATH"
    nix flake update --extra-experimental-features nix-command --extra-experimental-features flakes
    echo "Flake inputs updated successfully"
}

cmd_update_nixpkgs() {
    echo "Updating nixpkgs..."
    cd "$FLAKE_PATH"
    nix flake update nixpkgs --extra-experimental-features nix-command --extra-experimental-features flakes
    echo "Nixpkgs updated successfully"
}

cmd_list_machines() {
    echo "Available machines:"
    printf '%s\n' "${MACHINES[@]}" | sed 's/^/  /'
}

cmd_status() {
    local machine="${1:-}"
    if [[ -z "$machine" ]]; then
        machine=$(get_current_machine)
        if [[ -z "$machine" ]]; then
            echo "Error: Machine name required and could not detect from hostname"
            print_usage
            exit 1
        fi
        echo "Detected machine from hostname: $machine"
    fi
    
    check_machine "$machine"
    echo "Generations for $machine:"
    echo ""
    
    # Check if system is installed
    if [[ -f "/etc/nixos/configuration.nix" ]]; then
        # Try to get generations info
        if command -v nixos-rebuild &> /dev/null; then
            local generations
            generations=$(nixos-rebuild list-generations 2>/dev/null || echo "")
            
            if [[ -n "$generations" ]]; then
                echo "Available Generations:"
                echo "$generations" | sed 's/^/  /'
            else
                echo "Unable to retrieve generations"
            fi
        else
            echo "nixos-rebuild not available"
        fi
    else
        echo "This machine doesn't appear to be the current system"
    fi
}

cmd_rebuild_all() {
    local verbose_flags=""
    
    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                verbose_flags="--verbose"
                shift
                ;;
            --show-trace)
                verbose_flags="$verbose_flags --show-trace"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo "Building all machine configurations..."
    cd "$FLAKE_PATH"
    
    local failed_machines=()
    
    for machine in "${MACHINES[@]}"; do
        echo ""
        echo "Building $machine..."
        # shellcheck disable=SC2086
        if nix build ".#nixosConfigurations.$machine.config.system.build.toplevel" --extra-experimental-features nix-command --extra-experimental-features flakes $verbose_flags 2>&1; then
            echo "✓ $machine built successfully"
        else
            echo "✗ Failed to build $machine"
            failed_machines+=("$machine")
        fi
    done
    
    echo ""
    if [[ ${#failed_machines[@]} -eq 0 ]]; then
        echo "All machines built successfully!"
    else
        echo "Failed to build the following machines:"
        printf '%s\n' "${failed_machines[@]}" | sed 's/^/  - /'
        return 1
    fi
}

cmd_health() {
    local health_script="$FLAKE_PATH/scripts/check-system-health.sh"
    
    if [[ ! -f "$health_script" ]]; then
        echo "Error: Health check script not found at $health_script"
        exit 1
    fi
    
    if [[ ! -x "$health_script" ]]; then
        echo "Making health check script executable..."
        chmod +x "$health_script"
    fi
    
    echo "Running system health check..."
    echo ""
    "$health_script"
}

cmd_gc() {
    echo "Running garbage collection..."
    
    # Delete old generations and clean up unused store paths
    sudo nix-collect-garbage -d
    
    echo "Garbage collection complete"
    echo "Note: Old system generations (>7 days) are automatically cleaned up weekly via nix.gc.automatic"
}

cmd_pull() {
    echo "Pulling latest changes from git..."
    cd "$FLAKE_PATH"
    git pull
    echo "Git pull completed successfully"
    
    # Re-execute the script with the same arguments, excluding 'pull'
    echo "Re-running script..."
    exec "$0" "$@"
}

# VM Creation Functions
check_libvirt() {
    if ! command -v virsh &> /dev/null; then
        echo "Error: virsh command not found. Is libvirt installed?"
        echo "Install with: nix-shell -p libvirt"
        exit 1
    fi
    
    if ! virsh -c qemu:///system list &> /dev/null; then
        echo "Error: Cannot connect to libvirt. Make sure:"
        echo "  1. libvirtd service is running: sudo systemctl start libvirtd"
        echo "  2. You are in the libvirtd group: groups | grep libvirtd"
        exit 1
    fi
}

prompt_with_default() {
    local prompt_text="$1"
    local default_value="$2"
    local result
    
    if [[ -n "$default_value" ]]; then
        read -p "$prompt_text [$default_value]: " result
        echo "${result:-$default_value}"
    else
        read -p "$prompt_text: " result
        echo "$result"
    fi
}

generate_nixos_vm_config() {
    local vm_name="$1"
    local vm_memory="$2"
    local vm_cpus="$3"
    local vm_disk="$4"
    local vm_dir="$FLAKE_PATH/machines/$vm_name"
    
    # Create VM directory
    mkdir -p "$vm_dir"
    
    # Generate configuration.nix
    cat > "$vm_dir/configuration.nix" << EOF
# Virtual machine configuration for $vm_name
{ config, pkgs, lib, ... }:

{
  imports = [
    ../../common/common.nix
    ./hardware-configuration.nix
  ];

  # Networking
  networking.hostName = "$vm_name";
  networking.networkmanager.enable = true;

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # System state version
  system.stateVersion = "25.05";
}
EOF

    # Generate hardware-configuration.nix (minimal for VM)
    cat > "$vm_dir/hardware-configuration.nix" << EOF
# Hardware configuration for $vm_name VM
{ config, lib, pkgs, modulesPath, ... }:

{
  imports = [ ];

  # Boot configuration
  boot.initrd.availableKernelModules = [ "sd_mod" "sr_mod" ];
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ];
  boot.extraModulePackages = [ ];
  
  # File systems (will be auto-detected on first boot)
  fileSystems."/" = {
    device = "/dev/disk/by-label/nixos";
    fsType = "ext4";
  };

  fileSystems."/boot" = {
    device = "/dev/disk/by-label/ESP";
    fsType = "vfat";
  };

  swapDevices = [ ];

  # Networking
  networking.useDHCP = lib.mkDefault true;

  # Hardware
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
EOF

    echo "Generated NixOS VM configuration in $vm_dir"
}

add_vm_to_flake() {
    local vm_name="$1"
    local flake_file="$FLAKE_PATH/flake.nix"
    local temp_file
    
    # Check if VM already exists in flake
    if grep -q "nixosConfigurations.$vm_name" "$flake_file"; then
        echo "Warning: VM $vm_name already exists in flake.nix"
        return 1
    fi
    
    # Create backup
    cp "$flake_file" "$flake_file.bak"
    
    # Find the insertion point (before the closing brace of nixosConfigurations)
    # We'll use awk to insert the new configuration
    temp_file=$(mktemp)
    
    # Read the flake and insert the new VM config before the closing brace of nixosConfigurations
    # Look for the pattern: "      };" that closes nixosConfigurations
    awk -v vm_name="$vm_name" '
        BEGIN { inserted = 0; in_nixos_config = 0 }
        /^      nixosConfigurations = \{/ { in_nixos_config = 1 }
        /^      \};$/ && in_nixos_config && !inserted {
            print "        # Virtual machine configuration"
            print "        " vm_name " = nixpkgs.lib.nixosSystem {"
            print "          inherit system;"
            print "          modules = ["
            print "            ./machines/" vm_name "/configuration.nix"
            print "            ./machines/" vm_name "/hardware-configuration.nix"
            print "          ];"
            print "        };"
            print ""
            inserted = 1
            in_nixos_config = 0
        }
        { print }
    ' "$flake_file" > "$temp_file"
    
    # Check if insertion was successful
    if grep -q "nixosConfigurations.$vm_name" "$temp_file"; then
        mv "$temp_file" "$flake_file"
        echo "Added $vm_name to flake.nix"
        rm -f "$flake_file.bak"
        return 0
    else
        echo "Error: Failed to add $vm_name to flake.nix"
        rm -f "$temp_file"
        mv "$flake_file.bak" "$flake_file"
        return 1
    fi
}

create_vm_disk() {
    local vm_name="$1"
    local disk_size="$2"
    local disk_path="$3"
    
    # Check if qemu-img is available
    if ! command -v qemu-img &> /dev/null; then
        echo "Error: qemu-img command not found"
        echo "Install with: nix-shell -p qemu"
        return 1
    fi
    
    # Validate disk size format (qemu-img accepts formats like 20G, 40GB, etc.)
    if [[ ! "$disk_size" =~ ^[0-9]+[GMK]?B?$ ]]; then
        echo "Error: Invalid disk size format: $disk_size"
        echo "Use format like: 20G, 40GB, 500M"
        return 1
    fi
    
    # Create disk image
    if [[ -f "$disk_path" ]]; then
        echo "Warning: Disk image $disk_path already exists"
        read -p "Overwrite? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            return 1
        fi
        rm -f "$disk_path"
    fi
    
    echo "Creating disk image: $disk_path ($disk_size)..."
    if qemu-img create -f qcow2 "$disk_path" "$disk_size"; then
        echo "Disk image created successfully"
        return 0
    else
        echo "Error: Failed to create disk image"
        return 1
    fi
}

create_libvirt_vm() {
    local vm_name="$1"
    local vm_memory="$2"
    local vm_cpus="$3"
    local disk_path="$4"
    local os_type="$5"
    local iso_path="${6:-}"
    local network_type="${7:-default}"
    
    # Convert memory to MB (support G, M, K suffixes)
    local memory_mb
    if [[ "$vm_memory" =~ ^([0-9]+)([GMK]?)(B?)$ ]]; then
        local mem_num="${BASH_REMATCH[1]}"
        local mem_unit="${BASH_REMATCH[2]}"
        
        case "$mem_unit" in
            G|"")
                memory_mb=$((mem_num * 1024))
                ;;
            M)
                memory_mb=$mem_num
                ;;
            K)
                memory_mb=$((mem_num / 1024))
                ;;
        esac
    else
        echo "Error: Invalid memory format: $vm_memory"
        return 1
    fi
    
    # Check if VM already exists
    if virsh -c qemu:///system dominfo "$vm_name" &> /dev/null; then
        echo "Error: VM '$vm_name' already exists"
        return 1
    fi
    
    # Check if virt-install is available
    if ! command -v virt-install &> /dev/null; then
        echo "Error: virt-install command not found"
        echo "Install with: nix-shell -p virt-manager"
        return 1
    fi
    
    # Create VM using virt-install
    local install_args=(
        --name "$vm_name"
        --memory "$memory_mb"
        --vcpus "$vm_cpus"
        --disk "path=$disk_path,format=qcow2,bus=virtio"
        --network "network=$network_type,model=virtio"
        --graphics "spice,listen=0.0.0.0"
        --video "qxl"
        --channel "spicevmc"
        --console "pty,target_type=serial"
        --noautoconsole
    )
    
    case "$os_type" in
        nixos)
            # For NixOS, we'll create an empty disk and let user install manually
            install_args+=(--os-variant "generic")
            install_args+=(--boot "hd")
            if [[ -n "$iso_path" && -f "$iso_path" ]]; then
                install_args+=(--cdrom "$iso_path")
            fi
            ;;
        linux)
            install_args+=(--os-variant "generic")
            if [[ -n "$iso_path" && -f "$iso_path" ]]; then
                install_args+=(--cdrom "$iso_path")
            else
                install_args+=(--boot "hd")
            fi
            ;;
        windows)
            install_args+=(--os-variant "win10")
            if [[ -n "$iso_path" && -f "$iso_path" ]]; then
                install_args+=(--cdrom "$iso_path")
            else
                install_args+=(--boot "hd")
            fi
            ;;
        *)
            install_args+=(--os-variant "generic")
            if [[ -n "$iso_path" && -f "$iso_path" ]]; then
                install_args+=(--cdrom "$iso_path")
            else
                install_args+=(--boot "hd")
            fi
            ;;
    esac
    
    echo "Creating VM '$vm_name' with libvirt..."
    echo "Memory: ${memory_mb}MB, CPUs: $vm_cpus, Disk: $disk_path"
    
    if sudo virt-install "${install_args[@]}"; then
        echo "VM '$vm_name' created successfully!"
        echo ""
        echo "To start the VM:"
        echo "  virsh start $vm_name"
        echo ""
        echo "To connect via virt-manager or:"
        echo "  virt-viewer $vm_name"
        return 0
    else
        echo "Error: Failed to create VM"
        return 1
    fi
}

cmd_create_vm() {
    local vm_name=""
    local vm_os=""
    local vm_memory="4G"
    local vm_cpus="2"
    local vm_disk="20G"
    local vm_network="default"
    local iso_path=""
    local generate_nixos_config=true
    local interactive_mode=true
    
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)
                vm_name="$2"
                interactive_mode=false
                shift 2
                ;;
            --os)
                vm_os="$2"
                interactive_mode=false
                shift 2
                ;;
            --memory|--mem)
                vm_memory="$2"
                interactive_mode=false
                shift 2
                ;;
            --cpus|--cpu)
                vm_cpus="$2"
                interactive_mode=false
                shift 2
                ;;
            --disk)
                vm_disk="$2"
                interactive_mode=false
                shift 2
                ;;
            --network)
                vm_network="$2"
                interactive_mode=false
                shift 2
                ;;
            --iso)
                iso_path="$2"
                shift 2
                ;;
            --no-nixos-config)
                generate_nixos_config=false
                shift
                ;;
            --interactive|-i)
                interactive_mode=true
                shift
                ;;
            -h|--help)
                cat << EOF
Usage: $0 create-vm [OPTIONS]

Create a new virtual machine using QEMU/KVM via libvirt.

Options:
  --name NAME           VM name (required in non-interactive mode)
  --os TYPE             OS type: nixos, linux, windows (default: nixos)
  --memory SIZE         Memory size (e.g., 4G, 8GB) (default: 4G)
  --cpus NUM            Number of CPU cores (default: 2)
  --disk SIZE           Disk size (e.g., 20G, 40GB) (default: 20G)
  --network TYPE        Network type: default, bridge, nat (default: default)
  --iso PATH            Path to ISO image for installation
  --no-nixos-config     Don't generate NixOS configuration files
  --interactive, -i     Force interactive mode
  -h, --help            Show this help message

Examples:
  $0 create-vm
  $0 create-vm --name myvm --os nixos --memory 8G --cpus 4 --disk 40G
  $0 create-vm --name win10 --os windows --memory 8G --cpus 4 --disk 100G --iso /path/to/windows.iso

EOF
                return 0
                ;;
            *)
                echo "Error: Unknown option '$1'"
                echo "Use --help for usage information"
                return 1
                ;;
        esac
    done
    
    # Check libvirt availability
    check_libvirt
    
    # Interactive mode
    if [[ "$interactive_mode" == "true" ]]; then
        echo "=========================================="
        echo "Virtual Machine Creation Wizard"
        echo "=========================================="
        echo ""
        
        # VM Name
        while [[ -z "$vm_name" ]]; do
            vm_name=$(prompt_with_default "VM name" "")
            if [[ -z "$vm_name" ]]; then
                echo "Error: VM name is required"
            fi
        done
        
        # Check if VM already exists
        if virsh -c qemu:///system dominfo "$vm_name" &> /dev/null; then
            echo "Error: VM '$vm_name' already exists"
            return 1
        fi
        
        # OS Type
        echo ""
        echo "OS Type:"
        echo "  1) NixOS (will generate flake config)"
        echo "  2) Other Linux"
        echo "  3) Windows"
        echo "  4) Other"
        read -p "Select OS type [1]: " os_choice
        os_choice="${os_choice:-1}"
        case "$os_choice" in
            1) vm_os="nixos" ;;
            2) vm_os="linux" ;;
            3) vm_os="windows" ;;
            4) vm_os="other" ;;
            *) vm_os="nixos" ;;
        esac
        
        # Memory
        vm_memory=$(prompt_with_default "Memory size (e.g., 4G, 8GB)" "4G")
        
        # CPUs
        vm_cpus=$(prompt_with_default "Number of CPU cores" "2")
        
        # Disk
        vm_disk=$(prompt_with_default "Disk size (e.g., 20G, 40GB)" "20G")
        
        # Network
        echo ""
        echo "Network type:"
        echo "  1) default (NAT)"
        echo "  2) bridge"
        read -p "Select network type [1]: " net_choice
        net_choice="${net_choice:-1}"
        case "$net_choice" in
            1) vm_network="default" ;;
            2) vm_network="bridge" ;;
            *) vm_network="default" ;;
        esac
        
        # ISO (optional)
        if [[ "$vm_os" != "nixos" ]] || [[ "$vm_os" == "nixos" ]]; then
            read -p "ISO image path (optional, press Enter to skip): " iso_path
        fi
        
        # NixOS config generation
        if [[ "$vm_os" == "nixos" ]]; then
            read -p "Generate NixOS configuration in flake? (Y/n): " gen_config
            if [[ "$gen_config" =~ ^[Nn]$ ]]; then
                generate_nixos_config=false
            fi
        else
            generate_nixos_config=false
        fi
    else
        # Non-interactive mode - validate required parameters
        if [[ -z "$vm_name" ]]; then
            echo "Error: --name is required in non-interactive mode"
            return 1
        fi
        
        if [[ -z "$vm_os" ]]; then
            vm_os="nixos"
        fi
    fi
    
    # Validate VM name (no spaces, alphanumeric and hyphens)
    if [[ ! "$vm_name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "Error: VM name can only contain alphanumeric characters, hyphens, and underscores"
        return 1
    fi
    
    # Set default disk path
    local disk_path="${HOME}/.local/share/libvirt/images/${vm_name}.qcow2"
    mkdir -p "$(dirname "$disk_path")"
    
    echo ""
    echo "=========================================="
    echo "Creating VM: $vm_name"
    echo "=========================================="
    echo "OS Type: $vm_os"
    echo "Memory: $vm_memory"
    echo "CPUs: $vm_cpus"
    echo "Disk: $vm_disk ($disk_path)"
    echo "Network: $vm_network"
    [[ -n "$iso_path" ]] && echo "ISO: $iso_path"
    echo "=========================================="
    echo ""
    
    # Generate NixOS config if requested
    if [[ "$vm_os" == "nixos" && "$generate_nixos_config" == "true" ]]; then
        echo "Generating NixOS VM configuration..."
        generate_nixos_vm_config "$vm_name" "$vm_memory" "$vm_cpus" "$vm_disk"
        
        echo "Adding VM to flake.nix..."
        if add_vm_to_flake "$vm_name"; then
            echo "✓ VM configuration added to flake.nix"
            echo ""
            echo "Note: You may need to rebuild the flake after adding the VM:"
            echo "  nix flake check"
        else
            echo "Warning: Could not add VM to flake.nix (may already exist)"
        fi
        echo ""
    fi
    
    # Create disk image
    echo "Creating disk image..."
    if ! create_vm_disk "$vm_name" "$vm_disk" "$disk_path"; then
        echo "Error: Failed to create disk image"
        return 1
    fi
    echo ""
    
    # Create libvirt VM
    echo "Creating libvirt VM..."
    if create_libvirt_vm "$vm_name" "$vm_memory" "$vm_cpus" "$disk_path" "$vm_os" "$iso_path" "$vm_network"; then
        echo ""
        echo "=========================================="
        echo "VM Creation Complete!"
        echo "=========================================="
        echo ""
        echo "VM Name: $vm_name"
        echo "Disk: $disk_path"
        if [[ "$vm_os" == "nixos" && "$generate_nixos_config" == "true" ]]; then
            echo "Config: $FLAKE_PATH/machines/$vm_name/"
            echo ""
            echo "Next steps for NixOS VM:"
            echo "1. Start the VM: virsh start $vm_name"
            echo "2. Connect to console: virsh console $vm_name"
            echo "3. Install NixOS using the generated configuration"
        fi
        echo ""
        return 0
    else
        echo "Error: Failed to create VM"
        # Clean up disk if VM creation failed
        [[ -f "$disk_path" ]] && rm -f "$disk_path"
        return 1
    fi
}

interactive_mode() {
    local current_machine
    current_machine=$(get_current_machine 2>/dev/null || echo "unknown")
    
    while true; do
        echo ""
        echo "=========================================="
        echo "NixOS Configuration Manager - $current_machine"
        echo "=========================================="
        echo "1. Build and apply configuration immediately"
        echo "2. Build and apply configuration on next boot"
        echo "3. Build configuration only"
        echo "4. Update all flake inputs"
        echo "5. Garbage collection"
        echo "6. List generations"
        echo "7. List available machines"
        echo "8. System health check"
        echo "9. Git pull and rerun"
        echo "q. Quit"
        echo "r. Reboot"
        echo "=========================================="
        read -rsn1 -p "Select an option: " choice
        echo ""
        echo ""
        
        case "$choice" in
            1)
                cmd_switch
                ;;
            2)
                cmd_boot
                ;;
            3)
                cmd_build
                ;;
            4)
                cmd_update
                ;;
            5)
                cmd_gc
                ;;
            6)
                cmd_status
                ;;
            7)
                cmd_list_machines
                ;;
            8)
                cmd_health
                ;;
            9)
                cmd_pull
                ;;
            q|Q)
                echo "Exiting..."
                exit 0
                ;;
            r|R)
                sudo reboot
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

main() {
    # If no arguments, try to launch TUI, fallback to interactive mode
    if [[ $# -eq 0 ]]; then
        # Check if TUI script exists and Python with rich is available
        local tui_script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manage.py"
        if [[ -f "$tui_script" ]] && command -v python3 &> /dev/null; then
            # Try to import rich to check if it's available
            if python3 -c "import rich" 2>/dev/null; then
                exec python3 "$tui_script"
            fi
        fi
        # Fallback to basic interactive mode
        interactive_mode
    fi
    
    local cmd="$1"
    shift
    
    case "$cmd" in
        switch)
            cmd_switch "$@"
            ;;
        boot)
            cmd_boot "$@"
            ;;
        build)
            cmd_build "$@"
            ;;
        dry-run)
            cmd_dry_run "$@"
            ;;
        rebuild-all)
            cmd_rebuild_all "$@"
            ;;
        update)
            cmd_update "$@"
            ;;
        update-nixpkgs)
            cmd_update_nixpkgs "$@"
            ;;
        pull)
            cmd_pull "$@"
            ;;
        list-machines)
            cmd_list_machines "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        health)
            cmd_health "$@"
            ;;
        gc)
            cmd_gc "$@"
            ;;
        create-vm)
            cmd_create_vm "$@"
            ;;
        -h|--help|help)
            print_usage
            ;;
        *)
            echo "Error: Unknown command '$cmd'"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
