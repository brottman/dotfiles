#!/usr/bin/env bash
# Script to manage NixOS configurations across multiple machines

set -e

MACHINES=("brian-laptop" "superheavy" "docker")
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
  rebuild-all           Build all machine configurations
  update                Update all flake inputs
  update-nixpkgs        Update nixpkgs only
  list-machines         List all available machines
  status [MACHINE]      Show status of a machine
  gc                    Garbage collect old generations

Examples:
  $0 switch brian-laptop
  $0 build superheavy
  $0 rebuild-all
  $0 update
  $0 list-machines

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
    sudo nixos-rebuild switch --flake ".#$machine"
}

cmd_build() {
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
    echo "Building $machine configuration..."
    cd "$FLAKE_PATH"
    nix build ".#nixosConfigurations.$machine.config.system.build.toplevel"
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
    nix flake update
    echo "Flake inputs updated successfully"
}

cmd_update_nixpkgs() {
    echo "Updating nixpkgs..."
    cd "$FLAKE_PATH"
    nix flake update nixpkgs
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
    echo "Status for $machine:"
    echo "  Hostname: $machine"
    echo "  Configuration path: $FLAKE_PATH/machines/$machine"
    
    # Check if system is installed
    if [[ -f "/etc/nixos/configuration.nix" ]]; then
        echo "  Installed: Yes"
        
        # Try to get current generation info
        if command -v nixos-rebuild &> /dev/null; then
            local current_gen
            current_gen=$(nixos-rebuild list-generations 2>/dev/null | tail -n 1 || echo "")
            
            if [[ -n "$current_gen" ]]; then
                echo "  Current Generation: $current_gen"
            else
                echo "  Current Generation: Unable to retrieve"
            fi
        else
            echo "  Current Generation: nixos-rebuild not available"
        fi
        
        # Check boot environment
        if [[ -d "/boot/efi" ]] || [[ -d "/boot" ]]; then
            echo "  Boot: Configured"
        else
            echo "  Boot: Not found"
        fi
    else
        echo "  Installed: No"
        echo "  Note: This machine doesn't appear to be the current system"
    fi
}

cmd_rebuild_all() {
    echo "Building all machine configurations..."
    cd "$FLAKE_PATH"
    
    local failed_machines=()
    
    for machine in "${MACHINES[@]}"; do
        echo ""
        echo "Building $machine..."
        if nix build ".#nixosConfigurations.$machine.config.system.build.toplevel" 2>&1; then
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

cmd_gc() {
    echo "Running garbage collection..."
    nix-collect-garbage --delete-older-than 7d
    echo "Garbage collection complete"
}

main() {
    if [[ $# -eq 0 ]]; then
        print_usage
        exit 0
    fi
    
    local cmd="$1"
    shift
    
    case "$cmd" in
        switch)
            cmd_switch "$@"
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
        list-machines)
            cmd_list_machines "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        gc)
            cmd_gc "$@"
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
