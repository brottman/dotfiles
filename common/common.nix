# Common configuration shared across all machines
{ config, pkgs, ... }:

{
  # System settings
  time.timeZone = "America/New_York";
  i18n.defaultLocale = "en_US.UTF-8";

  # Nix settings
  nix = {
    settings = {
      auto-optimise-store = true;
      cores = 0;
      max-jobs = "auto";
      experimental-features = [ "nix-command" "flakes" ];
    };
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 7d";
    };
  };

  # Boot environment cleanup
  boot.loader.systemd-boot.configurationLimit = 10;
  boot.loader.timeout = 1;

  # System packages available on all machines
  environment.systemPackages = with pkgs; [
    aria2
    conda
    git
    vim
    nano
    curl
    wget
    htop
    btop
    tmux
    openssh
    shellcheck
    docker
    docker-compose
  ];

  # User configuration
  users.users.brian = {
    isNormalUser = true;
    home = "/home/brian";
    createHome = true;
    shell = pkgs.bash;
    extraGroups = [ "wheel" "networkmanager" "docker" "libvirtd" "kvm" "tailscale" ];
  };

  # Sudo configuration
  security.sudo.enable = true;
  security.sudo.wheelNeedsPassword = false;

  # Docker configuration
  virtualisation.docker = {
    enable = true;
    autoPrune.enable = true;
  };

  # SSH configuration
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = true;
      PubkeyAuthentication = true;
      PermitRootLogin = "yes";
      X11Forwarding = false;
      AllowUsers = [ "brian" ];
    };
  };

  # Tailscale configuration
  services.tailscale.enable = true;

  # System version (auto-managed by flakes)
  system.stateVersion = "25.05";
}
