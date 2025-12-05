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
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC2z5mEFsDVbBjQS/s7+jGveoc3735pGTbDmY/5khAiNm2+0sxsmPSEe9bPD4udUxMDwhNO5xsVrlfFbCqZ1Qa6t6g8xtnvJK38tt8YuJxNQdW4ozjID+ogGzDFglK/3A9nenpSD8oEskQN3B/ssYCIoAIJA7ABEiG/NOsFEW9el1xiVs/1JB7jpYygCFiH/ibUkNCs2BEVg4BN3IHzk/tbZZSQcHePp9xv7p4M88tIfmFQSo0HgOwGQooISLKDpfK4Xr8v78ZZcAkdmiMao2BmxJv734ioqOkcmdDbfLYotmHtZLfI42upVglK6K+SKeoFZ4FsG+8lCxllrQQCQUN7XRkQKJV+I5fskTCrolxu88r6QaoCCKk/rjpjs8pYJhCG8skRjRmcoli6dRRcYQoWC8m9zytRuplRchpoQU/6wSLIDRkbW0t1BCV7YlkgDw+qev5Ug25hBzVjIVAAH3yoRAa541kspwMl5oywHCwtYGxuAaksC3mZJgyMsULnAeM0VaE36vsxG2XpcNB4nJinJ9uujNipyUoAb4fjyhr9UD8y47MArwhXluXaUwDhwhiNvza1gKiXvzW0iuEEiR0NY8ig4ImP/108nffuPPKFsuwVIbWgXGYvmqkNflUmQOlogBhyPZIH7xPcd4rVVydmVgFJ9Wym2qiITp6nSmGj9w== brottman@gmail.com" # docker
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCqlwaCME2K5OoHRzmOaJp6OT1nHjuLBxhv7TRuEAo7TjqOIJm6Tm/oBM+h+A9mnxeasBV5EshSnQ5kKkXuCLqKommS6PibER1JaY37NIP8LRwSyP+cY5KW//SYh9mYdBpNt1JrhivIDOc8SuEZl7vmk3Ym/lSUsg5AjU6Z+RN+ItC5MCUWsB//X0mTt4208AegK7Kp12GGeEjct4iXOullHLXbjoG37XuVmq/yU41gYOmBWk4yK+vBC6UZqoWUWpmiIfBKJDQQHXvJ/X26P/X/VlAfKzC1MBM2leyXNO1ueI8lj2zpM8AGSFb9Hs6bo9qTIAJauEkG4uL/kXxrvogHub2V38hSqEq27rGGJ2bZn/MkEJBFTvqBrJ3zwf8s8XIDraCcvwCGOetFphsM+AeH2xa2IOYfbAOE8D8vc4W7o2PMB4HIgR2mr2sgwEPpBgAXqtYXbxzYqryMCHEBZ/3YL3ZiE3PiZCJpAkhnAiwMwDKgmzU34GASepqJEThoVTnaxDWCX7DduRHOvMpWBgt7LO5GcJTp+dbqH7eShyxiN28nwRjO0oVfg3+Wpn+V9l0B5S3LKgFYgSM/Uj3dsBr7EVVKtiDS4Y12sRRs/Yej5xzIPMZ5smGdIxs8ruZN/3H2uMsEjgAKyAmawfSWX3RAfSSZf57MjP5YnijMOy+x4Q== brottman@gmail.com" # superheavy
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
