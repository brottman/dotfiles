# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    #./samba-cups.nix
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
    
  ];

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



  # System state version (override common default)
  system.stateVersion = "25.05";
}
