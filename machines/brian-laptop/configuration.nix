# Laptop machine configuration
{ config, pkgs, lib, ... }:

{
  imports = [
    ../../common/common.nix
    ./vms.nix
  ];

  # Allow unfree packages
  nixpkgs.config.allowUnfree = true;

  # Allow insecure packages
  nixpkgs.config.permittedInsecurePackages = [ "ventoy-1.1.07" ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Use latest kernel
  boot.kernelPackages = pkgs.linuxPackages_latest;

  # Enable bcachefs support
  boot.supportedFilesystems = [ "bcachefs" ];

  # Boot configuration
  boot.initrd.kernelModules = [ ];

  # Quiet boot
  boot.kernelParams = [
    "quiet"
    "loglevel=3"
  ];
  boot.consoleLogLevel = 0;
  boot.initrd.verbose = false;

  # Networking
  networking.hostName = "brian-laptop";
  networking.networkmanager.enable = true;

  # Graphics (Intel integrated + NVIDIA)
  services.xserver = {
    enable = true;
    videoDrivers = [ "nvidia" ];
  };
  services.desktopManager.plasma6.enable = true;
  services.displayManager.sddm.enable = true;
  services.displayManager.sddm.wayland.enable = true;
  
  # Disable KDE Plasma's power button handler
  environment.etc."xdg/kdedefaults/powermanagementrc".text = ''
    [General]
    powerButtonAction=0
  '';
  services.displayManager.autoLogin = {
    enable = true;
    user = "brian";
  };

  # Intel graphics
  hardware.graphics = {
    enable = true;
  };

  # NVIDIA graphics
  hardware.nvidia = {
    modesetting.enable = true;
    powerManagement.enable = true;
    powerManagement.finegrained = true;
    prime.offload.enable = true;
    prime.intelBusId = "PCI:0:2:0";
    prime.nvidiaBusId = "PCI:1:0:0";
    package = config.boot.kernelPackages.nvidiaPackages.production;
    open = false;
    nvidiaSettings = true;
  };

  # Power management for laptop
  services.power-profiles-daemon.enable = false;
  services.tlp = {
    enable = true;
    settings = {
      CPU_SCALING_GOVERNOR_ON_AC = "performance";
      CPU_SCALING_GOVERNOR_ON_BAT = "powersave";
      ENERGY_PERF_POLICY_ON_AC = "performance";
      ENERGY_PERF_POLICY_ON_BAT = "power";
    };
  };

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # Disable screen blanking
  services.xserver.serverFlagsSection = ''
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
  '';

  # Power button action
  services.logind.settings = {
    Login = {
      HandlePowerKey = "reboot";
      HandlePowerKeyLongPress = "poweroff";
    };
  };

  # Sound
  services.pulseaudio.enable = false;
  services.pipewire = {
    enable = true;
    pulse.enable = true;
    alsa.enable = true;
  };

  # Bluetooth
  hardware.bluetooth = {
    enable = true;
    powerOnBoot = true;
  };
  #services.blueman.enable = true;

  # Trackpad
  services.libinput = {
    enable = true;
    touchpad = {
      naturalScrolling = true;
      tapping = true;
    };
  };

  # Steam
  programs.steam = {
    enable = true;
    remotePlay.openFirewall = true;
    dedicatedServer.openFirewall = true;
  };

  # AppImage support
  programs.appimage.enable = true;
  programs.appimage.binfmt = true; # For NixOS 24.05+


  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 80 443 ];
    allowedUDPPorts = [ ];
  };

  # Nginx web server
  services.nginx = {
    enable = true;
    virtualHosts = {
      "localhost" = {
        root = "/home/brian/html";
        listen = [
          { addr = "0.0.0.0"; port = 80; }
        ];
        locations."/".extraConfig = "autoindex on;";
      };
    };
  };

  # Ollama
  services.ollama = {
    enable = true;
    acceleration = "cuda";
  };

  # Additional packages for laptop
  environment.systemPackages = with pkgs; [
    anki
    antigravity
    appimage-run
    bluez
    bluez-tools
    google-chrome
    code-cursor
    codenomad
    devenv
    dtrx # file extractor
    exiftool
    ffmpeg
    filezilla
    fsearch
    gimp
    gocryptfs
    joplin-desktop
    kdePackages.kcalc
    lmstudio
    lutris
    nodejs
    opencode
    pinta
    prismlauncher
    python3
    qimgv
    rclone
    remmina
    restic
    rustdesk
    shellcheck
    seafile-client
    srm
    thunderbird
    tor
    tor-browser
    qbittorrent
    scrcpy
    gzdoom
    ventoy
    virt-manager
    vlc
    vscode-fhs
    wine
    zoom-us
  ];

  # Environment variables
  environment.variables = {
    # Add environment variables here
  };

  # Environment aliases
  environment.shellAliases = {
    update = "sudo nixos-rebuild switch --flake ~/dotfiles#brian-laptop";
    gc = "sudo nix-collect-garbage -d";
    sm = "~/dotfiles/sm";
    sysmanage = "~/dotfiles/sm";
    ff = "fastfetch";
    lock = "sudo umount /data/archive/plain";
    #unlock = "sudo mount /dev/disk/by-uuid/04966b6f-b27c-4b47-a589-c3243e9a03bf /data/archive/plain";
    unlock = "gocryptfs /data/archive/cipher/ /data/archive/plain/";
    clean = "srm -rfv /home/brian/.cache/thumbnails/;
            srm -rfv /home/brian/.config/gthumb/history.xbel;
            srm -rfv /home/brian/.config/gwenviewrc;
            srm -rfv /home/brian/.config/vlc/vlc-qt-interface.conf;
            srm -rfv '/home/brian/.tor project/';
            srm -rfv '/home/brian/.cache/tor project/';
            srm -rfv '/home/brian/.tor project/';";
    reboot = "sudo systemctl reboot";
    shutdown = "sudo systemctl poweroff";
    comfyui = "python /data/archive/ComfyUI/main.py";
    comfyui89 = "python /data/archive/plain/ComfyUI/main.py";
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
