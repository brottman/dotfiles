# Docker machine configuration (minimal, Docker-only)
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
  ];

  # Bootloader
  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
  };

  # Networking
  networking.hostName = "docker";
  networking.networkmanager.enable = true;

  # No GUI
  services.xserver.enable = false;

  # Docker packages
  environment.systemPackages = with pkgs; [
    docker
    docker-compose
  ];

  # Enable Docker
  virtualisation.docker = {
    enable = true;
    autoPrune.enable = true;
  };

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # SSH configuration for docker server
  services.openssh = {
    enable = true;
    port = 2222;
    settings = {
      PermitRootLogin = "no";
      PasswordAuthentication = false;
      PubkeyAuthentication = true;
      X11Forwarding = false;
      AllowUsers = [ "user" ];
      ClientAliveInterval = 300;
      ClientAliveCountMax = 2;
    };
  };

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 2222 ]; # SSH on non-standard port
    allowedUDPPorts = [ ];
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
