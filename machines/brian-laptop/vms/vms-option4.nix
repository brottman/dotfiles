# Option 4: Full VM with Disk Creation (Advanced)
# This approach includes disk image creation as part of the VM definition
# Best for: Complete declarative VM management including storage
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

  # Create ISOs directory for storage pool
  systemd.services.create-isos-directory = {
    description = "Create ISOs directory for libvirt storage pool";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.coreutils}/bin/mkdir -p /var/lib/libvirt/images/ISOs";
    };
    wantedBy = [ "multi-user.target" ];
    before = [ "create-vm-disk-example.service" ];
  };

  # Create disk image if it doesn't exist
  systemd.services.create-vm-disk-example = {
    description = "Create disk image for example-vm";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p /var/lib/libvirt/images";
      ExecStart = "${pkgs.qemu}/bin/qemu-img create -f qcow2 /var/lib/libvirt/images/example-vm.qcow2 20G";
    };
    wantedBy = [ "multi-user.target" ];
    before = [ "define-vm-example.service" ];
    unitConfig.ConditionPathExists = "!/var/lib/libvirt/images/example-vm.qcow2";
  };

  # Define the VM domain (using external XML file)
  systemd.services.define-vm-example = {
    description = "Define VM: example-vm";
    after = [ "libvirtd.service" "create-vm-disk-example.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./example-vm.xml}";
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
}

