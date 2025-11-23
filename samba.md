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

The configuration is ready to deploy. After rebuilding and rebooting, the file shares and print server will be available on your network.

