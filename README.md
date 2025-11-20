# NixOS Flakes Configuration for Multiple Machines

This repository contains a NixOS flakes configuration that manages three different machines: brian-laptop, superheavy, and docker.

## Structure

```
.
├── flake.nix                 # Main flake configuration
├── common/
│   └── common.nix           # Shared configuration for all machines
├── machines/
	│   ├── brian-laptop/
	│   │   ├── configuration.nix        # Laptop-specific config
	│   │   ├── hardware-configuration.nix
	│   │   └── home.nix                 # Home-manager config
	│   ├── superheavy/
│       ├── configuration.nix        # Server-specific config
│       └── hardware-configuration.nix
│   └── docker/
│       ├── configuration.nix        # Docker-specific config
│       └── hardware-configuration.nix
└── README.md
```

## Prerequisites

- NixOS installed with flakes enabled
- Git repository initialized in this directory

## Setup Instructions

### 1. Generate Hardware Configuration

For each machine, generate the hardware-specific configuration:

```bash
sudo nixos-generate-config --no-filesystems --show-hardware-config > path/to/hardware-configuration.nix
```

Update the UUIDs in each `hardware-configuration.nix` file with actual values from your system.

### 2. Update User Configuration

Edit the home-manager configurations in each machine's `home.nix`:
- Set your Git username and email
- Adjust package selections as needed

### 3. Build and Switch

To apply the configuration on each machine:

```bash
# On brian-laptop
sudo nixos-rebuild switch --flake .#brian-laptop

# On superheavy
sudo nixos-rebuild switch --flake .#superheavy

# On docker
sudo nixos-rebuild switch --flake .#docker
```

## Building

To just build the configuration without applying it:

```bash
nix build .#nixosConfigurations.brian-laptop.config.system.build.toplevel
nix build .#nixosConfigurations.superheavy.config.system.build.toplevel
nix build .#nixosConfigurations.docker.config.system.build.toplevel
```

## Usage

### Update Flake Inputs

To update all dependencies:

```bash
nix flake update
```

To update specific inputs:

```bash
nix flake update nixpkgs
nix flake update home-manager
```

### Enter Development Shell

```bash
nix flake show
nix develop
```

## Customization

### Adding a New Machine

1. Create a new directory under `machines/`
2. Create `configuration.nix`, `hardware-configuration.nix`, and optionally `home.nix`
3. Add a new entry to `nixosConfigurations` in `flake.nix`
4. Customize settings as needed

### Modifying Common Configuration

Edit `common/common.nix` to change settings applied to all machines.

## Machine-Specific Features

### Brian-Laptop
- Intel integrated graphics
- GNOME desktop environment
- Power management (TLP)
- Touchpad support

### Superheavy
- Minimal installation (no GUI)
- Docker support
- Nginx with SSL/ACME support
- PostgreSQL and Redis
- Fail2ban

### Docker
- Minimal installation (no GUI)
- Docker and docker-compose
- Auto-cleanup of unused Docker resources
- SSH enabled for remote access
- Optimized for running containerized applications

## Troubleshooting

### Flakes not enabled
If you get errors about flakes not being enabled, add to `/etc/nix/nix.conf`:
```
experimental-features = nix-command flakes
```

### Hardware configuration issues
Run `sudo nixos-generate-config` on each machine to get accurate hardware information.

### Home-manager issues
Ensure `home-manager` and `nixpkgs` versions are compatible by using the `follows` directive in `flake.nix`.

## Notes

- All machines use the same user `user` with sudo privileges
- SSH is configured but requires public key authentication
- State version is locked to `24.05` - update carefully if needed
