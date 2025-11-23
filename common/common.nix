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
    openssh.authorizedKeys.keys = [
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDCitDIYLLTrs3UuaH2BfJqzoCN3l111jAQyOsrg/1EiLwnO32eZJo2d9Wu1Y3Y26PsO/EfMgzJEo7DTxkAAyH1kk9aeE/lG4hQpB9Jus6ySUaAE9jhhSE6Ss8ZF345+QrWZfs1GSl4aGb7sKaKd87tSDHPnuI2Z1Har6CVo5CG/VqYeiNpFE8K3Fdg1M13QRXAmQrG2/U1Z2GHSEbGQu/HcebVElQj7YFgculo2PfR8ZenmZU2l7snVeium/n96OvQYqTfnCmRyZ2eoUYvoGHXwijDvzadlMm3q6cQ+xs4eHmKqttTVSqm1Ty7lhTZ7oucnOkTdoDq4siCQ6rpXwyDclRTG/tAB6DBi++jZD8Z/4ecHQQmjfJ7zmWtpjKMH9gCoFmRPM/dSeiNB4fzps73OLBhHgP35WV5XuHtoL08w8UVRZrxKvhBtc8lnwlWHTRfpPicvUojX7gYmqfck3htmMhSQrOp8w95vUQR/hHtSkTmGyqpdkHM2erhA+DjXLq6yAPftFmh+c1JsP24UzrHHM+kFXSGs5KLVRoI+7EK5h9Cd8Ax5aHoTF+fBG3jgrZOvuWKMocP65Pq+xEdrNHN8yy5P4/5SY1YaXfIJH3OukqQ5t2VKP7ljnZHTNO0c9s9I9yvsTGq8TBGUEdhDUiwcJ+4WMkFq0o1x4YFhH9ksQ== your_email@example.com" # Paste your public key here
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
