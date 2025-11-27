# sops-nix Setup Guide

This guide will walk you through setting up sops-nix for your NixOS configuration.

## What's Been Done

✅ sops-nix added to `flake.nix`  
✅ Secrets directory structure created  
✅ `.sops.yaml` configuration template created  
✅ `.gitignore` updated to exclude private keys  
✅ `superheavy/configuration.nix` updated to use sops-nix  
✅ Setup scripts and documentation created  

## Step-by-Step Setup

### Step 1: Generate Age Keys

Run the key generation script:

```bash
cd ~/dotfiles
./scripts/setup-sops-keys.sh
```

This will:
- Generate age keys for all machines (superheavy, brian-laptop, docker, backup)
- Save private keys to `secrets/keys/`
- Display public keys for each machine

**Important**: The private keys are automatically added to `.gitignore` and should NEVER be committed.

### Step 2: Configure .sops.yaml

Edit `secrets/.sops.yaml` and add the public keys:

```bash
# Get the public keys
cat secrets/keys/superheavy.age | grep "public key:"
cat secrets/keys/brian-laptop.age | grep "public key:"
```

Update `secrets/.sops.yaml`:

```yaml
creation_rules:
  - path_regex: secrets/superheavy\.yaml$
    age: age1abc123...xyz789  # Replace with actual superheavy public key
  
  - path_regex: secrets/brian-laptop\.yaml$
    age: age1def456...uvw012  # Replace with actual brian-laptop public key
  
  - path_regex: secrets/common\.yaml$
    age: >-
      age1abc123...xyz789,  # superheavy
      age1def456...uvw012   # brian-laptop
```

### Step 3: Create Encrypted Secrets File

Create the encrypted secrets file for superheavy:

```bash
# Copy the template
cp secrets/superheavy.yaml.template secrets/superheavy.yaml

# Edit with sops (it will encrypt on save)
sops secrets/superheavy.yaml
```

Add your actual secrets:

```yaml
# Postfix Gmail app password
postfix_gmail_password: "yayv haqb iaqd tehs"

# Samba password for brian user
samba_brian_password: "your-samba-password-here"
```

Save the file (sops will automatically encrypt it).

### Step 4: Deploy Private Key to superheavy

**One-time setup on the superheavy machine:**

```bash
# SSH to superheavy, then:
sudo mkdir -p /etc/sops/age
sudo cp ~/dotfiles/secrets/keys/superheavy.age /etc/sops/age/keys.txt
sudo chmod 600 /etc/sops/age/keys.txt
```

**Alternative**: If you're setting this up from your laptop:

```bash
# From your laptop
scp secrets/keys/superheavy.age superheavy:/tmp/superheavy.age

# Then on superheavy:
sudo mkdir -p /etc/sops/age
sudo mv /tmp/superheavy.age /etc/sops/age/keys.txt
sudo chmod 600 /etc/sops/age/keys.txt
```

### Step 5: Test the Configuration

Build the configuration to verify it works:

```bash
# On superheavy
cd ~/dotfiles
sudo nixos-rebuild switch --flake .#superheavy
```

If successful, the secrets will be decrypted and available at:
- `/run/secrets/postfix_gmail_password`
- `/run/secrets/samba_brian_password`

### Step 6: Verify Services

Check that Postfix and Samba are using the secrets:

```bash
# Check Postfix is running
sudo systemctl status postfix

# Check Samba is running
sudo systemctl status smb

# Verify the secret files exist (they should be readable)
sudo ls -la /run/secrets/
```

## What Changed

### Before (Insecure)

In `machines/superheavy/configuration.nix`:
```nix
environment.etc."postfix-setup/gmail_password".text = "brottman@gmail.com yayv haqb iaqd tehs";
```

This password was visible in:
- Git history
- Plaintext in the repository
- Anyone with repo access could see it

### After (Secure)

1. Password is encrypted in `secrets/superheavy.yaml`
2. Configuration references the secret:
   ```nix
   sops.secrets.postfix_gmail_password = {};
   ```
3. Service reads from `/run/secrets/postfix_gmail_password`
4. Password is never in plaintext in git

## Adding More Secrets

To add a new secret:

1. **Edit the encrypted file**:
   ```bash
   sops secrets/superheavy.yaml
   ```

2. **Add the secret**:
   ```yaml
   new_api_key: "secret-value"
   ```

3. **Update configuration.nix**:
   ```nix
   sops.secrets.new_api_key = {
     owner = "username";
     mode = "0400";
   };
   ```

4. **Use it in your config**:
   ```nix
   config.sops.secrets.new_api_key.path
   ```

5. **Rebuild**:
   ```bash
   sudo nixos-rebuild switch --flake .#superheavy
   ```

## Troubleshooting

### "Failed to decrypt secret"

- Verify the age key exists: `sudo ls -la /etc/sops/age/keys.txt`
- Check permissions: `sudo chmod 600 /etc/sops/age/keys.txt`
- Verify the public key in `.sops.yaml` matches the private key

### "sops command not found"

Install sops:
```bash
nix profile install nixpkgs#sops
# or
nix develop  # Enters dev shell with sops
```

### "Permission denied" when reading secrets

Check the secret configuration in `configuration.nix`:
```nix
sops.secrets.my_secret = {
  owner = "username";
  group = "groupname";
  mode = "0600";
};
```

### Build fails with "sops-nix not found"

Update your flake:
```bash
nix flake update
```

## Security Best Practices

1. ✅ **Never commit private keys** - They're in `.gitignore`
2. ✅ **Backup private keys** - Store them in a password manager
3. ✅ **Use separate keys per machine** - Limits blast radius
4. ✅ **Rotate keys periodically** - Generate new keys and re-encrypt
5. ✅ **Review `.sops.yaml`** - Ensure only authorized machines can decrypt

## Next Steps

- [ ] Generate age keys for all machines
- [ ] Configure `.sops.yaml` with public keys
- [ ] Create encrypted secrets files
- [ ] Deploy private keys to machines
- [ ] Test the configuration
- [ ] Remove hardcoded passwords from git history (optional, requires force-push)

## Additional Resources

- [sops-nix documentation](https://github.com/Mic92/sops-nix)
- [Mozilla SOPS documentation](https://github.com/mozilla/sops)
- See `SOPS-NIX-EXPLANATION.md` for detailed explanation
- See `secrets/README.md` for ongoing usage

