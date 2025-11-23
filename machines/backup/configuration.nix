# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    #./timers.nix
  ];

  # ZFS support
  boot.supportedFilesystems = [ "zfs" ];
  boot.zfs.extraPools = [ "backpool" ];
  boot.kernelParams = [ "zfs.zfs_arc_max=12884901888" ];
  services.zfs.autoScrub.enable = true;
  services.zfs.trim.enable = true;
  networking.hostId = "033c4bf0";
  services.zfs.autoSnapshot = {
    enable = true;
    frequent = 24;
    hourly = 48;
    daily = 60;
    weekly = 16;
    monthly = 60; # 5 years
  };

  # Networking
  networking.hostName = "backup";
  networking.networkmanager.enable = true;

  # No GUI
  services.xserver.enable = false;

  # Packages
  environment.systemPackages = with pkgs; [
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
    allowedTCPPorts = [ 22 ]; # SSH
    allowedUDPPorts = [ ];
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
