# Superheavy File Sharing and Print Server Configuration

I've configured superheavy as a file sharing and print server. Here's what was added:

## File Sharing (Samba/SMB)
- Enabled Samba with user-based security
- Configured two shares:
  - **`public`**: Guest-accessible at `/mnt/datapool/shared`
  - **`private`**: Requires authentication (user: brian) at `/mnt/datapool/private`
- Opened firewall ports: TCP 445 (SMB), UDP 137-138 (NetBIOS)

## Print Server (CUPS)
- Enabled CUPS with common printer drivers (gutenprint, cups-bjnp, cups-filters)
- Enabled network sharing and browsing
- Enabled Avahi for printer discovery
- Opened firewall port: TCP 631 (IPP)

## Next Steps

After deploying this configuration:

1. **Create the Samba share directories:**
   ```bash
   sudo mkdir -p /mnt/datapool/shared /mnt/datapool/private
   sudo chmod 755 /mnt/datapool/shared /mnt/datapool/private
   ```

2. **Set up Samba user password** (for the `brian` user):
   ```bash
   sudo smbpasswd -a brian
   ```

3. **Add printers** via:
   - Web interface: `http://superheavy:631`
   - Command line: `lpadmin`

4. **Adjust share paths** if your ZFS datapool is mounted elsewhere (check with `zfs list`).

## Adding Additional Samba Users

To add more Samba users to the configuration, edit `machines/superheavy/samba-cups.nix` and uncomment the `users` list in the `services.samba` section. There are two approaches:

### Option 1: Using sops-nix (Recommended for secrets)
If you're using `sops-nix` for secrets management:
```nix
services.samba = {
  # ... existing config ...
  users = [
    {
      name = "brian";
      passwordFile = config.sops.secrets.samba_brian_password.path;
    }
    {
      name = "alice";
      passwordFile = config.sops.secrets.samba_alice_password.path;
    }
  ];
};
```

### Option 2: Manual password management
Alternatively, manage passwords manually after deployment:
```bash
sudo smbpasswd -a username
```

**Important:** The system user must exist in your NixOS configuration (`users.users`) before you can add them as a Samba user.

The configuration is ready to deploy. After rebuilding and rebooting, the file shares and print server will be available on your network.

