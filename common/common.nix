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
      download-buffer-size = 536870912; # 512 MiB
      
      # Binary caches for faster builds (especially CUDA/Ollama dependencies)
      substituters = [
        "https://cache.nixos.org"
        "https://nix-community.cachix.org"
      ];
      trusted-public-keys = [
        "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
        "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs="
      ];
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
    fastfetch
    git
    vim
    nano
    curl
    wget
    btop
    tmux
    openssh
    shellcheck
    docker
    docker-compose
    python3Packages.rich
    python3Packages.textual
    smartmontools
    speedtest-cli
  ];

  # User configuration
  users.users.brian = {
    isNormalUser = true;
    home = "/home/brian";
    createHome = true;
    shell = pkgs.bash;
    extraGroups = [ "wheel" "networkmanager" "docker" "tailscale" ];
    openssh.authorizedKeys.keys = [
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCXtn51o0N4KzZtexd2fxtWdDXu/uJGuJx++P6rTnxiGPzRzK1S1rL6iimx7VWiFIuV6elIPXYS79jEyEzuJnSFmnCTQRCnG/RP7M0xV70pd9wmmYr5ABHCAcAqS97KnFcahI2A1tXWVg4kRy/3OFhWoGIdfBTCKfYSoi52s5Pdbf7WucsLzq8VVcL4kx1hVdSmvcsKt5F9ZF2YczAdhXLp8V44Q0YSfViaUvjWtzLmvQL4HtKkOM/J2m9f3GLQKLrq03KgE2DDZGFXL9HNYQ3nO2pC5/mx4Z7cAWc4KqjH7apLHQqkFxmSxwV73jyx0hLyKFtEAFVMkVYfACdmBJTVbac0Od5sF3uuYfoe8LThVw+LPxTnQ9ybCz0IT55M01FJfdJBJZ+GD/slpsnRwRDH3l66ro1pBYBjAxQlax7RvqZ0AwTTI67iow+XVpomX9G0vbxFOo+S6G0i6TqGtrG3KMgHfqfM/jvhIzSebSJbh71+dmdquorqfeWYu4cnoRzlU/zwt0wIII6fQpokbsddiwIFaZBwAuZod8J87xqxZded83mII5wr41EzpIyzvFCf4Ne+t5AdDx3MHUFOhRdMv6Kwi+tqKsDeU3lLxmhIzpqWzM/XacfimwZyYHgRPtyEy6xrTxHtFnVrlB04UQweNTnhuzFeCYCxt2XZ8wfglw== brottman@gmail.com" # brian-laptop
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC9xNjU0/799DczpokbfkpkcuHrkKjqFA7Ka3OTS+gqduht5MSVgx5v/G41iVLaddmEMTrOZAglrtJZQ1LXzSL4uZkpGENO0RDQbhlUI4kx9EQyz1ufni7W0tXz1OC4HB5qQiN9dl1Atvc64GwPZpylz49GOY7+9uzZ9CO5kYxbvyF6zkyfqwy7NDn7v3SX7oJDgQfgRTqUe6O1y58bKFME4LUNjZz9bz/5ndPYe8Pvsjnbnwxct3uK/qByhC6/GgfRI4NPUnV1mmu/4UJTWI6Tv2aFHiLptWFYo+1mAbTCEk1q/4fNfwf5gB1yUlFbzve6L2iZbwkQLQzRuogBUUisCv3E5DIPJX3MilF+1tKVQ0hRHC9dMVsy4pKhjHw08ymqJJkbXBMZr4poiyEwDN5DPbizyO9u8HJU96txy0/BRqWj2KNGMMr228d6u1JEAfnl+Jc2R0Cmw5B5LEtTU8SgtXqc1WdGYb1GoCChwDrKQ4is1Gyc8tHZ/G5ghZcj6qbvOfMOE32LA/7QtK/g4tpdWsd6wbKC7+OeE3MmVs7q3daCWtB1PlMbKGDPEEY14dC3/J/EWVl3H2FA7WqQ4+KjsTZyZCauvrxHo00Zq6j8KHSc0jZhEgLZe67LuNFkuinY3qBsswbw3/8XkWqUF8vlkj+D+Nly9M5aYwb4iMfiuw== brottman@gmail.com" # backup
    ];
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
      PermitRootLogin = "no";
      X11Forwarding = false;
      AllowUsers = [ "brian" ];
    };
  };

  # Tailscale configuration
  services.tailscale.enable = true;

  # System version (auto-managed by flakes)
  system.stateVersion = "25.05";
}
