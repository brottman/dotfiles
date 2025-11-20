# Superheavy server hardware configuration
{ config, lib, pkgs, ... }:

{
  imports = [ ];

  # Boot configuration
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ];
  boot.extraModulePackages = [ ];
  
  # Bootloader settings for server (UEFI)
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

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
  
  # Server-specific: kernel modules for virtualization and high-performance workloads
  boot.kernelModules = [ "kvm-intel" "kvm-amd" ]; # Adjust based on CPU
}
