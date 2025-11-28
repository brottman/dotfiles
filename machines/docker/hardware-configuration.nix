# Docker server hardware configuration
{ config, lib, pkgs, modulesPath, ... }:

{
  imports = [ ];

  # Boot configuration
  boot.initrd.availableKernelModules = [ "sd_mod" "sr_mod" ];
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ]; # Adjust based on CPU
  boot.extraModulePackages = [ ];
  
  # Bootloader settings for server (systemd-boot)
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # File systems - REPLACE UUIDs with actual device UUIDs from `nixos-generate-config`
  fileSystems."/" = {
    device = "/dev/disk/by-uuid/b3f13945-5faa-463b-beeb-68bc5e1a9e0f";
    fsType = "ext4";
  };

  fileSystems."/boot" = {
    device = "/dev/disk/by-uuid/322B-CD11";
    fsType = "vfat";
    options = [ "fmask=0022" "dmask=0022" ];
  };

  swapDevices = [ ];

  # Networking
  networking.useDHCP = lib.mkDefault true;

  # Hardware
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}