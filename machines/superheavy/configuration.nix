# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
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

  # Server packages
  environment.systemPackages = with pkgs; [
    nginx
    postgresql
    redis
  ];

  # Nginx
  services.nginx = {
    enable = false; # Set to true when ready to deploy
    virtualHosts."example.com" = {
      forceSSL = true;
      enableACME = true;
      locations."/" = {
        proxyPass = "http://localhost:3000";
      };
    };
  };

  # Security.acme for SSL certificates
  security.acme = {
    acceptTerms = true;
    defaults.email = "brottman@gmail.com";
  };

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # Fail2ban
  services.fail2ban.enable = true;

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 
                                          22 # ssh
                                          80 # npm
                                          443 # npm
                                          445 # samba
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
    allowedUDPPorts = [ ];
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
