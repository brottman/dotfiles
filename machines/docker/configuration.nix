# Server machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
  ];

  # Networking
  networking.hostName = "docker";
  networking.networkmanager.enable = true;
  networking.interfaces.eth0.ipv4.addresses = [
    {
      address = "192.168.1.12";
      prefixLength = 24;
    }
  ];
  networking.defaultGateway = "192.168.1.1";
  networking.nameservers = [ "192.168.1.15" ];

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
                                          81 # npm
                                          443 # npm
                                          9000 # portainer
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
