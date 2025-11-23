# Server machine configuration
{ config, pkgs, lib, ... }:

{
  imports = [
    ../../common/common.nix
    ./samba-cups.nix
    ./timers.nix
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

  # Packages
  environment.systemPackages = with pkgs; [
    conda
    doublecmd
    libatasmart
    lzop
    mbuffer
    sanoid
    mailutils
    postfix
  ];

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # Email notifications for system events
  # Local mail service with Gmail relay
  services.postfix = {
    enable = true;
    relayHost = "smtp.gmail.com";
    relayPort = 587;
    origin = "superheavy";
    hostname = "superheavy";
    domain = "brottman.local";
    networks = [ "127.0.0.0/8" "10.0.0.0/8" "192.168.0.0/16" ];
    
    # Additional Postfix configuration for Gmail relay
    config = {
      smtp_use_tls = "yes";
      smtp_sasl_auth_enable = "yes";
      smtp_sasl_security_options = "noanonymous";
      smtp_sasl_password_maps = "hash:/etc/postfix/gmail_password";
      smtp_tls_CAfile = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      inet_protocols = "ipv4";
      sender_canonical_maps = "regexp:/etc/postfix/sender_canonical";
      sender_canonical_classes = "envelope_sender, header_sender";
    };
  };

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



  # System state version (override common default)
  system.stateVersion = "25.05";
}
