# SSH Inter-Machine Trust Setup Guide

This guide explains how to set up SSH trust between your machines using the `machine-secrets` module.

## Step 0: Generate SSH Keys on Each Machine

Before you can SSH between machines, each machine needs a private SSH key. On each machine, run:

```bash
bash ~/dotfiles/generate-ssh-keys.sh
```

This will:
1. Create `~/.ssh/id_ed25519` if it doesn't exist
2. Output your public key

**You must run this on each machine first, before proceeding to Step 1.**

## Step 1: Gather SSH Host Public Keys

You need to collect the SSH host public key from each machine. On each machine, run:

```bash
ssh-keyscan localhost
```

Or to get the ed25519 key specifically:

```bash
ssh-keyscan -t ed25519 localhost
```

Example output:
```
localhost ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyHere
```

The key part after `ssh-ed25519` is what you need.

### For all machines in your setup:

**brian-laptop:**
```bash
# On brian-laptop
ssh-keyscan -t ed25519 localhost
# or use: hostname -I to get IP, then: ssh-keyscan -t ed25519 <IP>
```

**superheavy:**
```bash
# On superheavy
ssh-keyscan -t ed25519 localhost
```

**docker:**
```bash
# On docker
ssh-keyscan -t ed25519 localhost
```

**backup:**
```bash
# On backup
ssh-keyscan -t ed25519 localhost
```

## Step 2: Collect Your SSH Public Keys

After running the key generation script on each machine, gather the public keys. The script already printed them, but you can also get them with:

```bash
cat ~/.ssh/id_ed25519.pub
```

The output will look like:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIXxxxxx... brian@machine-name
```

You need to copy the **entire line** (the full key with the `ssh-ed25519` prefix).

### Collect from all machines:

- Run `cat ~/.ssh/id_ed25519.pub` on **brian-laptop** and copy the output
- Run `cat ~/.ssh/id_ed25519.pub` on **superheavy** and copy the output
- Run `cat ~/.ssh/id_ed25519.pub` on **backup** and copy the output
- Run `cat ~/.ssh/id_ed25519.pub` on **docker** and copy the output

## Step 3: Configure machine-secrets in Each Machine

Once you have all the keys, update each machine's configuration to include:

### Example: brian-laptop

Add this to `machines/brian-laptop/configuration.nix`:

```nix
machine-secrets = {
  sshKeys = {
    enable = true;
    
    # Your laptop's host key (so other machines can SSH to it)
    hostPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx... brian-laptop";
    
    # Authorized keys for the brian user on this machine
    authorizedKeys = {
      brian = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx... brian@laptop"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIyyyyy... brian@superheavy"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIzzzzz... brian@docker"
      ];
    };
  };
  
  # Store the host public keys of machines you want to SSH to
  trustedMachines = {
    "superheavy" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIyyyyy... superheavy";
    "docker" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIzzzzz... docker";
    "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIwwwww... backup";
  };
};
```

### Example: superheavy

Add this to `machines/superheavy/configuration.nix`:

```nix
machine-secrets = {
  sshKeys = {
    enable = true;
    hostPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIyyyyy... superheavy";
    authorizedKeys = {
      brian = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx... brian@laptop"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIyyyyy... brian@superheavy"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIzzzzz... brian@docker"
      ];
    };
  };
  
  trustedMachines = {
    "laptop" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx... laptop";
    "docker" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIzzzzz... docker";
    "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIwwwww... backup";
  };
};
```

Repeat for `docker` and `backup` machines similarly.

## Step 4: Apply Configuration

On each machine, apply the new configuration:

```bash
sudo nixos-rebuild switch --flake .#brian-laptop
sudo nixos-rebuild switch --flake .#superheavy
sudo nixos-rebuild switch --flake .#docker
sudo nixos-rebuild switch --flake .#backup
```

## Step 5: Test SSH Connectivity

Test SSH between machines (assumes you've set up DNS or `/etc/hosts`):

```bash
# From laptop to superheavy
ssh brian@superheavy

# From superheavy to laptop
ssh brian@laptop

# From any machine to docker
ssh brian@docker
```

## Optional: Add to /etc/hosts

For easier testing, add entries to `/etc/hosts` on each machine. You can do this in `common.nix`:

```nix
networking.hosts = {
  "192.168.1.10" = [ "superheavy" ];
  "192.168.1.20" = [ "docker" ];
  "192.168.1.30" = [ "backup" ];
  "192.168.1.40" = [ "laptop" ];
};
```

Replace IPs with your actual machine IPs.

## Option: Global Authorized Keys

If you have a master SSH key you want authorized on all machines, use `globalAuthorizedKeys`:

```nix
machine-secrets = {
  sshKeys = {
    enable = true;
    hostPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx...";
    globalAuthorizedKeys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAImaster... master-key"
    ];
    authorizedKeys = {
      brian = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx... brian@laptop"
      ];
    };
  };
};
```

This adds the master key to all users' authorized_keys files.

## Troubleshooting

### "Permission denied (publickey,keyboard-interactive)"

This error means the SSH server is not accepting your public key. Try:

1. **Verify your private key exists on the client machine:**
   ```bash
   ls -la ~/.ssh/id_ed25519
   ```
   If it doesn't exist, run: `bash ~/dotfiles/generate-ssh-keys.sh`

2. **Verify the public key is in authorized_keys on the target machine:**
   ```bash
   cat ~/.ssh/authorized_keys
   ```
   The key from your client machine should be listed there.

3. **Check SSH service is running on the target machine:**
   ```bash
   sudo systemctl status sshd
   ```

4. **Test with verbose output to see what's happening:**
   ```bash
   ssh -vvv brian@<target-machine>
   ```
   Look for lines like "Offering public key:" to see which keys are being tried.

5. **Verify the configuration was applied:**
   ```bash
   sudo nixos-rebuild switch --flake .#<machine-name>
   ```
   Then restart SSH: `sudo systemctl restart sshd`

## Security Notes

- **Never commit private SSH keys** to git
- Host public keys (which are already public) can be safely stored in the repo
- User public keys (for authorized_keys) can be safely stored in the repo
- Keep your NixOS repo access restricted if you're storing SSH public keys
- Consider using `agenix` or `sops-nix` for higher security if needed
