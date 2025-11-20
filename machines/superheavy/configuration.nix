# Server machine configuration
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

  # ZFS support
  boot.supportedFilesystems = [ "zfs" ];
  services.zfs.autoScrub.enable = true;
  services.zfs.trim.enable = true;

  # Networking
  networking.hostName = "superheavy";
  networking.networkmanager.enable = true;

  # No GUI
  services.xserver.enable = false;

  # Server packages
  environment.systemPackages = with pkgs; [
    docker
    docker-compose
    nginx
    postgresql
    redis
  ];

  # Enable Docker
  virtualisation.docker = {
    enable = true;
    autoPrune.enable = true;
  };

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

  # SSH configuration for superheavy server
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
      MaxAuthTries = 3;
    };
  };

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 2222 80 443 ]; # SSH on non-standard port, HTTP, HTTPS
    allowedUDPPorts = [ ];
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
