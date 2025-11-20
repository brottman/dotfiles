# Laptop machine configuration
{ config, pkgs, ... }:

{
  imports = [
    ../../common/common.nix
    ../../common/machine-secrets.nix
  ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Networking
  networking.hostName = "laptop";
  networking.networkmanager.enable = true;

  # Graphics (Intel integrated)
  services.xserver = {
    enable = true;
    videoDrivers = [ "intel" ];
    desktopManager.plasma5.enable = true;
    displayManager.sddm.enable = true;
    displayManager.sddm.wayland.enable = true;
  };

  # Intel graphics
  hardware.opengl = {
    enable = true;
    driSupport = true;
  };

  # Power management for laptop
  services.power-profiles-daemon.enable = true;
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
  services.logind.extraConfig = ''
    HandlePowerKey=poweroff
  '';

  # Sound
  hardware.pulseaudio.enable = false;
  services.pipewire = {
    enable = true;
    pulse.enable = true;
    alsa.enable = true;
  };

  # Trackpad
  services.xserver.libinput = {
    enable = true;
    trackpad = {
      naturalScrolling = true;
      tapping = true;
    };
  };

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ ];
    allowedUDPPorts = [ ];
  };

  # Additional packages for laptop
  environment.systemPackages = with pkgs; [
    firefox
    vscode
    thunderbird
    lutris
  ];

  # System state version (override common default)
  system.stateVersion = "25.05";
}
