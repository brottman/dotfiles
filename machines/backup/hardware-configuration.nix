# Backup server hardware configuration
{ config, lib, pkgs, ... }:

{
  imports = [ ];

  # Boot configuration
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ];
  boot.extraModulePackages = [ ];
  
  # Bootloader settings for server
  # The GRUB bootloader is configured in the machine configuration (../configuration.nix)
  # Avoid setting a bootloader here to prevent duplicate definitions of
  # system.build.installBootLoader.

  # File systems - REPLACE UUIDs with actual device UUIDs from `nixos-generate-config`
  fileSystems."/" = {
    device = "/dev/disk/by-uuid/REPLACE-WITH-UUID";
    fsType = "ext4";
  };

  fileSystems."/boot" = {
    device = "/dev/disk/by-uuid/REPLACE-WITH-BOOT-UUID";
    fsType = "vfat";
  };

  swapDevices = [
    { device = "/dev/disk/by-uuid/REPLACE-WITH-SWAP-UUID"; }
  ];

  # Networking
  networking.useDHCP = lib.mkDefault true;

  # Hardware
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
