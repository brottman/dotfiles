# sops-nix Explanation and Setup Guide

## What is sops-nix?

**sops-nix** integrates Mozilla SOPS (Secrets OPerationS) with NixOS, allowing you to:
- Store secrets (passwords, API keys, certificates) in encrypted files
- Commit encrypted secrets to git safely
- Decrypt secrets automatically during NixOS rebuild
- Control access per-machine or per-user using age keys or PGP

## How It Works

### 1. **Encryption Process (Development)**

```
┌─────────────────┐
│ secrets.yaml    │  ← Plaintext secrets file
│ (unencrypted)   │
└────────┬────────┘
         │
         │ sops encrypt
         │ (uses age key)
         ▼
┌─────────────────┐
│ secrets.yaml    │  ← Encrypted file (safe for git)
│ (encrypted)     │
└─────────────────┘
```

### 2. **Decryption Process (Deployment)**

```
┌─────────────────┐
│ secrets.yaml    │  ← Encrypted file from git
│ (encrypted)     │
└────────┬────────┘
         │
         │ sops-nix decrypts
         │ (uses age key from /run/secrets)
         ▼
┌─────────────────┐
│ /run/secrets/   │  ← Decrypted secrets available
│   secret_name   │     to NixOS services
└─────────────────┘
```

### 3. **Key Management**

sops-nix uses **age** (modern encryption) or **PGP** keys:
- **Age keys**: Simple, fast, recommended
- **Master key**: Encrypts the age keys themselves
- **Machine keys**: Each machine has its own age key
- **Access control**: Define which machines/users can decrypt which secrets

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Your Repository                       │
│                                                          │
│  flake.nix                                              │
│    └─> inputs.sops-nix                                  │
│                                                          │
│  machines/superheavy/configuration.nix                  │
│    └─> imports sops-nix module                          │
│    └─> config.sops.secrets.*                            │
│                                                          │
│  secrets/                                               │
│    ├─> .sops.yaml          ← SOPS configuration        │
│    ├─> secrets.yaml        ← Encrypted secrets         │
│    └─> keys/                                               │
│        ├─> superheavy.age   ← Machine-specific key       │
│        └─> brian-laptop.age ← Machine-specific key       │
└─────────────────────────────────────────────────────────┘
```

## Step-by-Step: How It Works

### Step 1: Generate Age Keys

Each machine needs its own age key:

```bash
# Generate a key for superheavy
age-keygen -o secrets/keys/superheavy.age

# Output:
# Public key: age1abc123...xyz789
# Private key saved to: secrets/keys/superheavy.age
```

**Important**: The private key file should be:
- Added to `.gitignore` (never commit private keys!)
- Copied to each machine at `/etc/sops/age/keys.txt` during initial setup

### Step 2: Configure SOPS

Create `.sops.yaml` in your `secrets/` directory:

```yaml
# .sops.yaml
creation_rules:
  # Rule for superheavy machine secrets
  - path_regex: secrets/superheavy\.yaml$
    age: >-
      age1abc123...xyz789  # superheavy's public key
  
  # Rule for brian-laptop machine secrets
  - path_regex: secrets/brian-laptop\.yaml$
    age: >-
      age1def456...uvw012  # brian-laptop's public key
  
  # Rule for secrets shared across all machines
  - path_regex: secrets/common\.yaml$
    age: >-
      age1abc123...xyz789,  # superheavy
      age1def456...uvw012   # brian-laptop
```

### Step 3: Create Encrypted Secrets File

Create `secrets/superheavy.yaml` (plaintext initially):

```yaml
# secrets/superheavy.yaml (before encryption)
samba_brian_password: "my-secure-password-123"
postfix_gmail_password: "kcxl zipl nlst opau"
api_key: "sk-1234567890abcdef"
```

Encrypt it:

```bash
sops --encrypt --in-place secrets/superheavy.yaml
```

Now the file looks like this (encrypted):

```yaml
# secrets/superheavy.yaml (after encryption)
samba_brian_password: ENC[AES256_GCM,data:...]
sops:
  version: 3.7.3
  age:
    - recipient: age1abc123...xyz789
      enc: |
        ...
```

### Step 4: Configure NixOS

In `flake.nix`, add sops-nix input:

```nix
inputs = {
  nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  sops-nix.url = "github:Mic92/sops-nix";
  sops-nix.inputs.nixpkgs.follows = "nixpkgs";
};
```

In `machines/superheavy/configuration.nix`:

```nix
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ./samba-cups.nix
    ./timers.nix
    # Add sops-nix module
    inputs.sops-nix.nixosModules.sops
  ];

  # Configure sops-nix
  sops = {
    # Path to your secrets file
    defaultSopsFile = ./secrets/superheavy.yaml;
    
    # Where to find the age key on this machine
    age.keyFile = "/etc/sops/age/keys.txt";
    
    # Define your secrets
    secrets = {
      # Samba password
      samba_brian_password = {
        # Optional: restrict permissions
        owner = "root";
        group = "root";
        mode = "0600";
      };
      
      # Postfix Gmail password
      postfix_gmail_password = {
        owner = "postfix";
        group = "postfix";
        mode = "0400";
      };
      
      # API key (as environment variable)
      api_key = {
        mode = "0400";
      };
    };
  };

  # Use the secrets in your services
  services.samba = {
    enable = true;
    users = [
      {
        name = "brian";
        passwordFile = config.sops.secrets.samba_brian_password.path;
      }
    ];
  };

  services.postfix = {
    enable = true;
    config = {
      smtp_sasl_password_maps = "hash:/var/lib/postfix/gmail_password";
    };
  };
  
  # Create the gmail_password file from secret
  systemd.services.postfix-db-setup = {
    script = ''
      echo "brottman@gmail.com ${builtins.readFile config.sops.secrets.postfix_gmail_password.path}" \
        | ${pkgs.postfix}/bin/postmap /var/lib/postfix/gmail_password
    '';
  };
}
```

### Step 5: Deploy

1. **Copy the age key to the machine** (one-time setup):
   ```bash
   # On superheavy machine
   sudo mkdir -p /etc/sops/age
   sudo cp secrets/keys/superheavy.age /etc/sops/age/keys.txt
   sudo chmod 600 /etc/sops/age/keys.txt
   ```

2. **Rebuild**:
   ```bash
   sudo nixos-rebuild switch --flake .#superheavy
   ```

3. **What happens**:
   - sops-nix reads the encrypted `secrets/superheavy.yaml`
   - Decrypts it using the age key from `/etc/sops/age/keys.txt`
   - Creates files in `/run/secrets/` with the decrypted values
   - Your services reference these files

## Real-World Example: Replacing Your Hardcoded Postfix Password

### Current (Insecure) Configuration

In `machines/superheavy/configuration.nix`:

```nix
environment.etc = {
  "postfix-setup/gmail_password".text = "brottman@gmail.com kcxl zipl nlst opau";
};
```

### With sops-nix (Secure)

1. **Create encrypted secret**:
   ```bash
   # Create secrets/superheavy.yaml
   sops secrets/superheavy.yaml
   # Add: postfix_gmail_password: "kcxl zipl nlst opau"
   ```

2. **Update configuration**:
   ```nix
   sops.secrets.postfix_gmail_password = {};
   
   systemd.services.postfix-db-setup = {
     script = ''
       echo "brottman@gmail.com ${builtins.readFile config.sops.secrets.postfix_gmail_password.path}" \
         | ${pkgs.postfix}/bin/postmap /var/lib/postfix/gmail_password
     '';
   };
   ```

3. **Remove hardcoded password** from git!

## Key Concepts

### 1. **Secret Paths**

After decryption, secrets are available at:
- `config.sops.secrets.secret_name.path` → `/run/secrets/secret_name`
- Services read from these paths
- Files are automatically cleaned up on reboot

### 2. **Access Control**

Control who can decrypt:
- **Per-machine**: Each machine has its own age key
- **Per-secret**: Different secrets encrypted with different keys
- **Shared secrets**: Encrypt with multiple public keys

### 3. **Secret Types**

```nix
sops.secrets = {
  # Simple file secret
  my_password = {};
  
  # With permissions
  my_key = {
    owner = "user";
    group = "user";
    mode = "0600";
  };
  
  # As environment variable
  api_key = {
    mode = "0400";
    # Use in systemd service:
    # EnvironmentFile = config.sops.secrets.api_key.path;
  };
};
```

## Security Best Practices

1. **Never commit private keys** - Add `secrets/keys/*.age` to `.gitignore`
2. **Use separate keys per machine** - Limits blast radius if one key is compromised
3. **Rotate keys periodically** - Generate new keys and re-encrypt secrets
4. **Use minimal permissions** - Set appropriate `owner`, `group`, `mode`
5. **Audit access** - Review `.sops.yaml` to see who can decrypt what

## Workflow

### Adding a New Secret

```bash
# 1. Edit encrypted file
sops secrets/superheavy.yaml

# 2. Add new secret:
# new_api_key: "secret-value"

# 3. Save (automatically encrypted)

# 4. Update configuration.nix
sops.secrets.new_api_key = {};

# 5. Rebuild
sudo nixos-rebuild switch --flake .#superheavy
```

### Rotating a Secret

```bash
# 1. Edit encrypted file
sops secrets/superheavy.yaml

# 2. Change the value
# old_password: "new-password-value"

# 3. Save and rebuild
```

### Adding a New Machine

```bash
# 1. Generate new age key
age-keygen -o secrets/keys/new-machine.age

# 2. Add public key to .sops.yaml
# 3. Copy private key to new machine: /etc/sops/age/keys.txt
# 4. Re-encrypt secrets with new key (if needed)
sops --encrypt --in-place secrets/common.yaml
```

## Troubleshooting

### "Failed to decrypt secret"

- Check age key is at `/etc/sops/age/keys.txt`
- Verify key permissions: `chmod 600 /etc/sops/age/keys.txt`
- Ensure public key in `.sops.yaml` matches the private key

### "Permission denied"

- Check secret file permissions in NixOS config
- Verify service user has access to `/run/secrets/`

### "sops command not found"

Install sops:
```bash
nix profile install nixpkgs#sops
# or
nix shell nixpkgs#sops
```

## Benefits for Your Setup

1. **Remove hardcoded passwords** from `superheavy/configuration.nix`
2. **Secure Samba passwords** (as mentioned in `samba.md`)
3. **API keys** for services like Ollama, Joplin, etc.
4. **Database passwords** for PostgreSQL
5. **SSH keys** or certificates
6. **Docker registry credentials**

All while keeping everything in git and maintaining declarative configuration!

