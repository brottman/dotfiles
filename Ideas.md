What I've Done
1. Enhanced machine-secrets.nix
Added comprehensive SSH key management options:

sshKeys.enable: Master toggle for SSH configuration
sshKeys.hostPublicKey: Your machine's SSH host public key (for other machines to trust it)
sshKeys.authorizedKeys: Per-user SSH public keys that can SSH into this machine
sshKeys.globalAuthorizedKeys: Keys authorized for all users
trustedMachines: Map of machine names to their host public keys (for known_hosts)

2. Created SSH Setup Guide (ssh-setup-guide.md)
A step-by-step guide explaining:

How to gather SSH host keys from each machine
How to collect SSH public keys
How to configure each machine with machine-secrets
How to apply and test the configuration
Security best practices

How It Works

The module automatically:

    Sets authorized keys for each user from your configuration
    Creates ssh_known_hosts with your trusted machines (avoiding "host key verification" prompts)
    Merges global authorized keys with user-specific keys

Next Steps

On each machine, collect its SSH host ed25519 key:

Collect SSH public keys from each user (or generate new ones)

Update each machine's configuration using the guide as template

Run sudo nixos-rebuild switch --flake .#<machine-name>

The setup is completely declarative—you can safely store it in git, and machines will automatically configure SSH trust when you rebuild.


conda env list

conda create -n comfyui
conda create -n skylight python=3.14
conda create -n stoxai python=3.12

conda activate comfyui
conda activate skylight
conda activate stoxai