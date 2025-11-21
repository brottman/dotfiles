# Laptop machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
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

  # Virtualization
  boot.kernelModules = [ "kvm-intel" ];
  boot.extraModprobeConfig = "options kvm_intel nested=1";

  # Quiet boot
  boot.kernelParams = [
    "quiet"
    "loglevel=3"
  ];
  boot.consoleLogLevel = 0;
  boot.initrd.verbose = false;

  # Disable Plymouth
  boot.plymouth.enable = false;

  # Networking
  networking.hostName = "laptop";
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
    settings = {
      General = {
        Enable = "Source,Sink,Media,Socket";
      };
    };
  };
  services.blueman.enable = true;

  # Trackpad
  services.libinput = {
    enable = true;
    touchpad = {
      naturalScrolling = true;
      tapping = true;
    };
  };

  # Virtualization
  virtualisation.libvirtd = {
    enable = true;
    onBoot = "start";
  };
  virtualisation.spiceUSBRedirection.enable = true;
  programs.virt-manager.enable = true;

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ ];
    allowedUDPPorts = [ ];
  };

  # Passwordless sudo for wheel group
  security.sudo.wheelNeedsPassword = false;

  # Additional packages for laptop
  environment.systemPackages = with pkgs; [
    anki
    bluez
    bluez-tools
    code-cursor
    dtrx # file extractor
    exiftool
    ffmpeg
    filezilla
    fsearch
    gimp
    gocryptfs
    joplin-desktop
    lmstudio
    lutris
    pinta
    prismlauncher
    rclone
    restic
    shellcheck
    seafile-client
    srm
    thunderbird
    qbittorrent
    scrcpy
    steam
    gzdoom
    ventoy
    vlc
    vscode
    wine
  ];

  # System state version (override common default)
  system.stateVersion = "25.05";
}
