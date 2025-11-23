# Samba and CUPS Configuration for superheavy
{ config, pkgs, ... }:

{
  # File Sharing - Samba
  services.samba = {
    enable = true;
    openFirewall = false; # We manage firewall manually
    securityType = "user";
    extraConfig = ''
      workgroup = WORKGROUP
      server string = superheavy
      netbios name = superheavy
      security = user
      hosts allow = 192.168. 10. 127. localhost
      hosts deny = 0.0.0.0/0
      guest account = nobody
      map to guest = Bad User
    '';
    shares = {
      public = {
        path = "/mnt/datapool/shared";
        browseable = "yes";
        "read only" = "no";
        "guest ok" = "yes";
        "create mask" = "0644";
        "directory mask" = "0755";
      };
      private = {
        path = "/mnt/datapool/private";
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
    drivers = with pkgs; [ gutenprint cups-bjnp cups-filters ];
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
    nssmdns = true;
    openFirewall = false; # We manage firewall manually
  };
}
