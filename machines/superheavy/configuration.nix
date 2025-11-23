# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
  ];

  # ZFS support
  boot.supportedFilesystems = [ "zfs" ];
  boot.zfs.extraPools = [ "datapool" ];
  boot.kernelParams = [ "zfs.zfs_arc_max=12884901888" ];
  services.zfs.autoScrub.enable = true;
  services.zfs.trim.enable = true;
  networking.hostId = "3744ab0e";
  services.zfs.autoSnapshot = {
    enable = true;
    frequent = 24;
    hourly = 48;
    daily = 60;
    weekly = 16;
    monthly = 60; # 5 years
  };

  # Networking
  networking.hostName = "superheavy";
  networking.networkmanager.enable = true;

  # No GUI
  services.xserver.enable = false;

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 
                                          22 # ssh
                                          80 # npm
                                          443 # npm
                                          445 # samba
                                          631 # cups/ipp
                                          3389 # rdp
                                          7878 # radarr
                                          8000 # skylight
                                          8083 # books
                                          8096 # jellyfin
                                          8989 # sonarr
                                          9000 # portainer
                                          9696 # prowlarr
                                          22300 # joplin
                                          32480 # sabnzbd
                                          32490 # qbittorrent
                                          39999 # dozzle
                                          ];
    allowedUDPPorts = [ 137 138 ]; # samba netbios
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

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

  # System state version (override common default)
  system.stateVersion = "25.05";
}
