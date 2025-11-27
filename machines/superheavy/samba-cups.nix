# Samba and CUPS Configuration for superheavy
{ config, pkgs, ... }:

{
  # File Sharing - Samba
  services.samba = {
    enable = true;
    openFirewall = false; # We manage firewall manually
    settings = {
      global = {
        workgroup = "WORKGROUP";
        "server string" = "superheavy";
        "netbios name" = "superheavy";
        security = "user";
        "passdb backend" = "tdbsam";
        "hosts allow" = "192.168.* 10.* 100.* 127.* localhost";
        "hosts deny" = "0.0.0.0/0";
        "guest account" = "nobody";
      };
      backup = {
        path = "/datapool/backup";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "no";
        "valid users" = "brian";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
      brian = {
        path = "/datapool/brian";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "no";
        "valid users" = "brian";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
      data = {
        path = "/datapool/data";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "no";
        "valid users" = "brian";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
      docker = {
        path = "/datapool/docker";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "no";
        "valid users" = "brian";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
      printer = {
        path = "/datapool/printer";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "no";
        "valid users" = "brian";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
    };
  };

  # Print Server - CUPS
  services.printing = {
    enable = true;
    drivers = with pkgs; [ gutenprint cups-bjnp cups-filters brlaser ];
    stateless = false;
    allowFrom = [ "all" ];
    listenAddresses = [ "*:631" ];
    defaultShared = true;
    browsing = true;
    openFirewall = false; # We manage firewall manually
  };

  # CUPS web interface and printer discovery
  services.avahi = {
    enable = true;
    nssmdns4 = true;
    openFirewall = false; # We manage firewall manually
  };

  # Set Samba password from SOPS secret
  systemd.services.samba-set-password = {
    description = "Set Samba password for brian user";
    after = [ "samba.service" "network.target" ];
    wants = [ "samba.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      SECRET_FILE="${config.sops.secrets.samba_brian_password.path}"
      
      # Wait for secret file to be available (with timeout)
      # Secrets are created during system activation, so they should exist
      # but we wait a bit in case activation is still running
      TIMEOUT=30
      ELAPSED=0
      while [ ! -f "$SECRET_FILE" ] && [ $ELAPSED -lt $TIMEOUT ]; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
      done
      
      if [ ! -f "$SECRET_FILE" ]; then
        echo "Error: Secret file $SECRET_FILE not found after $TIMEOUT seconds"
        echo "This usually means sops-nix activation hasn't completed yet."
        exit 1
      fi
      
      PASSWORD=$(cat "$SECRET_FILE")
      
      # Check if user already exists in Samba
      if ! ${pkgs.samba}/bin/pdbedit -L 2>/dev/null | grep -q "^brian:"; then
        # Add user and set password from file
        printf "%s\n%s\n" "$PASSWORD" "$PASSWORD" | ${pkgs.samba}/bin/smbpasswd -a -s brian
      else
        # Update password if user exists
        printf "%s\n%s\n" "$PASSWORD" "$PASSWORD" | ${pkgs.samba}/bin/smbpasswd -s brian
      fi
    '';
  };

}
