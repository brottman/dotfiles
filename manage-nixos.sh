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
  list-machines         List all available machines
  status [MACHINE]      Show status of a machine
  gc                    Garbage collect old generations

Options:
  -v, --verbose         Show verbose output during build
  --show-trace          Show full stack traces for errors

Examples:
  $0 switch brian-laptop
  $0 boot brian-laptop
  $0 build superheavy --verbose
  $0 rebuild-all --show-trace
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
                echo ""
                echo "Current Generation: $(echo "$generations" | tail -n 1 | awk '{print $1}' | sed 's/^/  /')"
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

cmd_gc() {
    echo "Running garbage collection..."
    
    # Delete old generations from boot loader
    echo "Deleting old boot entries..."
    sudo nix-collect-garbage -d
    
    # Clean up unused store paths
    echo "Cleaning up unused store paths..."
    sudo nix store gc --debug
    
    echo "Garbage collection complete"
    echo "Note: Run 'nix-collect-garbage --delete-older-than 7d' to also delete generations older than 7 days"
}

interactive_mode() {
    while true; do
        echo ""
        echo "=========================================="
        echo "NixOS Configuration Manager"
        echo "=========================================="
        echo "1. Build and apply configuration immediately"
        echo "2. Build and apply configuration on next boot"
        echo "3. Build configuration only"
        echo "4. Update all flake inputs"
        echo "5. Garbage collection"
        echo "6. List generations"
        echo "7. List available machines"
        echo "0. Exit"
        echo "=========================================="
        read -p "Select an option: " choice
        echo ""
        
        case "$choice" in
            1)
                cmd_build && cmd_switch
                exit 0
                ;;
            2)
                cmd_build && cmd_boot
                read -p "Would you like to reboot now? (y/n): " reboot_choice
                if [[ "$reboot_choice" == "y" || "$reboot_choice" == "Y" ]]; then
                    sudo reboot
                else
                    exit 0
                fi
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
            0)
                echo "Exiting..."
                exit 0
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

main() {
    # If no arguments, enter interactive mode
    if [[ $# -eq 0 ]]; then
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
