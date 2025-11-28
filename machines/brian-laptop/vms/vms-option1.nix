# Option 1: Individual VM Services (Simple, explicit)
# This approach defines each VM as a separate systemd service
# Best for: Small number of VMs, maximum clarity
# See OPTIONS-INDEX.md for comparison of all options
{ config, pkgs, lib, ... }:

{
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

  # Define VM: example-vm (using external XML file)
  systemd.services.define-vm-example = {
    description = "Define VM: example-vm";
    after = [ "libvirtd.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./guestvm.xml}";
    };
    wantedBy = [ "multi-user.target" ];
  };

  # Optionally auto-start the VM on boot
  systemd.services.autostart-vm-example = {
    description = "Autostart VM: example-vm";
    after = [ "define-vm-example.service" "libvirtd.service" ];
    requires = [ "define-vm-example.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh autostart example-vm";
    };
    wantedBy = [ "multi-user.target" ];
  };

  # Define another VM: another-vm
  systemd.services.define-vm-another = {
    description = "Define VM: another-vm";
    after = [ "libvirtd.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./another-vm.xml}";
    };
    wantedBy = [ "multi-user.target" ];
  };
}

