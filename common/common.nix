# Common configuration shared across all machines
{ config, pkgs, ... }:

{
  # System settings
  time.timeZone = "UTC";
  i18n.defaultLocale = "en_US.UTF-8";

  # Nix settings
  nix = {
    settings = {
      auto-optimise-store = true;
      cores = 0;
      max-jobs = "auto";
    };
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 7d";
    };
  };

  # System packages available on all machines
  environment.systemPackages = with pkgs; [
    git
    vim
    nano
    curl
    wget
    htop
    btop
    tmux
    openssh
  ];

  # User configuration
  users.users.brian = {
    isNormalUser = true;
    home = "/home/brian";
    createHome = true;
    shell = pkgs.bash;
    groups = [ "wheel" ];
    extraGroups = [ "networkmanager" "docker" ];
  };

  # Sudo configuration
  security.sudo.enable = true;

  # SSH configuration
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      PubkeyAuthentication = true;
      PermitRootLogin = "no";
      X11Forwarding = false;
      AllowUsers = [ "brian" ];
    }
  };

  # System version (auto-managed by flakes)
  system.stateVersion = "25.05";
}
