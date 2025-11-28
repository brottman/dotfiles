# Option 2: Helper Function + List (Scalable, clean)
# This approach uses helper functions to generate services for multiple VMs
# Best for: Multiple VMs, maintainable and DRY
# See OPTIONS-INDEX.md for comparison of all options
{ config, pkgs, lib, ... }:

let
  # Helper function to define a VM domain
  defineVM = name: {
    description = "Define VM: ${name}";
    after = [ "libvirtd.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./${name}.xml}";
    };
    wantedBy = [ "multi-user.target" ];
  };

  # Helper function to auto-start a VM
  autostartVM = name: {
    description = "Autostart VM: ${name}";
    after = [ "define-vm-${name}.service" "libvirtd.service" ];
    requires = [ "define-vm-${name}.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh autostart ${name}";
    };
    wantedBy = [ "multi-user.target" ];
  };

  # List of VMs to manage
  managedVMs = [ "example-vm" "another-vm" "third-vm" ];
  autoStartVMs = [ "example-vm" ];  # Only auto-start specific VMs

in {
  # Virtualisation: libvirtd for VM management
  virtualisation.libvirtd = {
    enable = true;
    qemu = {
      package = pkgs.qemu_kvm;
      swtpm.enable = true;
    };
  };

  # Add user to libvirt group for VM management
  users.users.brian.extraGroups = [ "libvirtd" ];

  # Generate systemd services for all VMs
  systemd.services = builtins.listToAttrs (
    map (vm: {
      name = "define-vm-${builtins.replaceStrings [ "-" ] [ "-" ] vm}";
      value = defineVM vm;
    }) managedVMs
  ) // builtins.listToAttrs (
    map (vm: {
      name = "autostart-vm-${builtins.replaceStrings [ "-" ] [ "-" ] vm}";
      value = autostartVM vm;
    }) autoStartVMs
  );
}

