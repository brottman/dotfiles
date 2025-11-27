# Secrets Management with sops-nix

This directory contains encrypted secrets managed by sops-nix.

## Directory Structure

```
secrets/
├── .sops.yaml              # SOPS configuration (defines encryption rules)
├── keys/                   # Private age keys (NEVER commit these!)
│   ├── superheavy.age
│   ├── brian-laptop.age
│   └── ...
├── superheavy.yaml         # Encrypted secrets for superheavy
├── brian-laptop.yaml       # Encrypted secrets for brian-laptop
└── common.yaml             # Encrypted secrets shared across machines
```

## Initial Setup

### 1. Generate Age Keys

Run the setup script to generate keys for all machines:

```bash
./scripts/setup-sops-keys.sh
```

This will create private keys in `secrets/keys/` for each machine.

### 2. Configure .sops.yaml

Edit `secrets/.sops.yaml` and add the public keys:

```bash
# Get public keys
cat secrets/keys/superheavy.age | grep "public key:"
cat secrets/keys/brian-laptop.age | grep "public key:"
```

Add them to the appropriate sections in `.sops.yaml`.

### 3. Create Encrypted Secrets Files

For each machine, create and encrypt secrets:

```bash
# Copy template
cp secrets/superheavy.yaml.template secrets/superheavy.yaml

# Edit with sops (will encrypt on save)
sops secrets/superheavy.yaml

# Or encrypt manually
sops --encrypt --in-place secrets/superheavy.yaml
```

### 4. Deploy Private Keys to Machines

**One-time setup on each machine:**

```bash
# On superheavy
sudo mkdir -p /etc/sops/age
sudo cp secrets/keys/superheavy.age /etc/sops/age/keys.txt
sudo chmod 600 /etc/sops/age/keys.txt
```

**Important**: Never commit private keys to git! They're in `.gitignore`.

## Editing Secrets

To edit an encrypted secrets file:

```bash
sops secrets/superheavy.yaml
```

This will:
1. Decrypt the file temporarily
2. Open it in your editor
3. Re-encrypt when you save

## Adding a New Secret

1. Edit the encrypted file:
   ```bash
   sops secrets/superheavy.yaml
   ```

2. Add the new secret:
   ```yaml
   new_secret: "value"
   ```

3. Save (automatically encrypted)

4. Update `machines/superheavy/configuration.nix`:
   ```nix
   sops.secrets.new_secret = {};
   ```

5. Use it in your config:
   ```nix
   config.sops.secrets.new_secret.path
   ```

## Security Notes

- ✅ Private keys are in `.gitignore` - never commit them
- ✅ Encrypted files are safe to commit
- ✅ Each machine only has access to its own secrets (unless shared)
- ✅ Secrets are decrypted at build time, not stored in plaintext
- ⚠️  Keep backups of private keys in a secure location (password manager, etc.)

## Troubleshooting

### "Failed to decrypt secret"

- Verify the age key is at `/etc/sops/age/keys.txt` on the machine
- Check file permissions: `sudo chmod 600 /etc/sops/age/keys.txt`
- Ensure the public key in `.sops.yaml` matches the private key

### "sops command not found"

Install sops:
```bash
nix profile install nixpkgs#sops
# or enter dev shell
nix develop
```

### "Permission denied" when reading secrets

Check the secret permissions in your NixOS config:
```nix
sops.secrets.my_secret = {
  owner = "username";
  group = "groupname";
  mode = "0600";
};
```

