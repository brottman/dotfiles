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
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCcfGONr+0FVO1v3OBaDiav2dE8ZKWo9A1rLUjqkrhRbm7subDiBjBpThuiWhxpHsU0OBYC6unaUn2/69cbbXWnRAewEU/yd5ggd50eHdU2IdfRa0ugAGxvo38wGhhAHxhb6QF3nYbOZuxeopsHrideoklONy4U2NLxGkb3XKKXJraSwfHgq9DUyazxXDKPj4vHlCI4IEfPecLTiruNz4W02NvVrc0S7Xy3E8YzwLTu8dnOIp9qOGyK/kBf6mYOAbZXkqz3GdjVqFpZsvzL9u+HPGTSybx1hTalEGc+BdECyKgGJI2pa1WPTMm+SUK1KzEpWpbJ8d2vCByKvc4J2azr9N1S/QonuPLRQqDnQN8XpkSzS0BTNUNA4y9hFJQ/pf4sH/LuqI8wGgFOcrzk3TU5B9bh2Lpw0+JZ7BfInvcm6/7AK1XZwgJ8GkY+VlEttsNpGaW7Km9PDbCjBRI1HIzCOGW6La1OxzmJPjO5TY7FDfTNx01mtKV7He9dhd95MTpLR3zx2Jhzk8aCDK/C9KM+8NQdvqwnbyTmTcYGISbbVGozIFk+rIzx8wSwS9VTmpXGDT4YeYmZs9Xkce3IfCFiGIbMqjx8RKBniStYsUX2Jlw/SlHKg8vxoIVVYxS0vMnuMH0dyths9iRPMlyyNI0YnGyFZ0O1JYiMe4hV3elbDw== brottman@gmail.com" # backup
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
