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
  systemd.services.define-guestvm = {
    description = "Define VM: guestvm";
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
  systemd.services.autostart-guestvm = {
    description = "Autostart VM: guestvm";
    after = [ "define-guestvm.service" "libvirtd.service" ];
    requires = [ "define-guestvm.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh autostart guestvm";
    };
    wantedBy = [ "multi-user.target" ];
  };

}

