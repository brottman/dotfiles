Implement the creation of virtual machines in the manage script. Ask various questions to help determine the configuration:

1, VM type:
    - QEMU/KVM via libvirt (recommended, already configured)
    - Other (specify)

2. OS:
    - NixOS VMs
    - Other Linux
    - Windows
    - Multiple options

3. Creation method:
    - Interactive script (prompts for settings)
    - Command-line tool with flags
    - Both

4. Default settings:
    - Memory (e.g., 4GB)
    - CPU cores (e.g., 2)
    - Disk size (e.g., 20GB)
    - Network (NAT, bridge, etc.)

5. Integration:
    - Add to manage-nixos.sh (e.g., create-vm)
    - Standalone script
    - Both
6. Features:
    - Auto-generate NixOS VM configs in the flake
    - Just create VM instances
    - Both