# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
  ];

  machine-secrets = {
    sshKeys = {
      enable = true;
      
      # Your laptop's host key (so other machines can SSH to it)
      hostPublicKey = "AAAAC3NzaC1lZDI1NTE5AAAAIHJM+DQTYuxIUkny90TbnL4xEfIN7jWzdhsFYkCDhePo backup";
      
      # Authorized keys for the brian user on this machine
      authorizedKeys = {
        brian = [
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIJO8uo1P2tkol5uYYPtn/+SPp3xMUTPyuURcgsyg0jk brian@laptop"
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJLMqTqjGGiFC8jjGi4hhXfk3mPz7ebJ8VJk5xaDmQb brian@superheavy"
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJM+DQTYuxIUkny90TbnL4xEfIN7jWzdhsFYkCDhePo brian@backup"
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILBVZabueeT2ESBtgz3blxhE39JQv736W0uDoZmRxP0D brian@docker"
        ];
      };
    };
    
    # Store the host public keys of machines you want to SSH to
    trustedMachines = {
      "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIJO8uo1P2tkol5uYYPtn/+SPp3xMUTPyuURcgsyg0jk brian@laptop";
      "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJLMqTqjGGiFC8jjGi4hhXfk3mPz7ebJ8VJk5xaDmQb brian@superheavy";
      "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJM+DQTYuxIUkny90TbnL4xEfIN7jWzdhsFYkCDhePo brian@backup";
      "backup" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILBVZabueeT2ESBtgz3blxhE39JQv736W0uDoZmRxP0D brian@docker";
    };
  };

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
    allowedTCPPorts = [ 22 ]; # SSH
    allowedUDPPorts = [ ];
    # Allow Docker to manage its own ports
    extraCommands = ''iptables -A INPUT -i docker0 -j ACCEPT'';
    extraStopCommands = ''iptables -D INPUT -i docker0 -j ACCEPT'';
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
