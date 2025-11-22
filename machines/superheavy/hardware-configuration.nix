# Superheavy server hardware configuration
{ config, lib, pkgs, ... }:

{
  imports = [ ];

  # Boot configuration
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ "kvm-intel" ];
  boot.extraModulePackages = [ ];
  
  # Bootloader settings for server
  # The GRUB bootloader is configured in the machine configuration (../configuration.nix)
  # Avoid setting a bootloader here to prevent duplicate definitions of
  # system.build.installBootLoader.

  # File systems - REPLACE UUIDs with actual device UUIDs from `nixos-generate-config`
  fileSystems."/" =
    { device = "/dev/disk/by-uuid/2062fb50-587c-4058-83f6-893113566b41";
      fsType = "ext4";
    };

  fileSystems."/boot" =
    { device = "/dev/disk/by-uuid/3E0A-9209";
      fsType = "vfat";
      options = [ "fmask=0022" "dmask=0022" ];
    };

  swapDevices = [ ];

  # Networking
  networking.useDHCP = lib.mkDefault true;

  # Hardware
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
