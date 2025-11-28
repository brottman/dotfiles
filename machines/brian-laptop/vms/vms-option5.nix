# Option 5: Inline XML in Systemd Service
# This approach defines the VM XML directly in the systemd service using a shell script
# Best for: Everything in Nix, no external XML files needed
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

  # Define the VM domain with inline XML
  systemd.services.define-vm-example = {
    description = "Define VM: example-vm";
    after = [ "libvirtd.service" "create-vm-disk-example.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = pkgs.writeShellScript "define-example-vm" ''
        # Undefine the VM if it already exists (idempotent operation)
        # This allows the configuration to be updated without manual intervention
        if ${pkgs.libvirt}/bin/virsh dominfo example-vm &>/dev/null; then
          ${pkgs.libvirt}/bin/virsh undefine example-vm || true
        fi
        
        # Define the VM
        ${pkgs.libvirt}/bin/virsh define /dev/stdin <<EOF
        <domain type='kvm'>
          <name>example-vm</name>
          <memory unit='KiB'>4194304</memory>
          <currentMemory unit='KiB'>4194304</currentMemory>
          <vcpu placement='static'>2</vcpu>
          <os>
            <type arch='x86_64' machine='pc-q35-9.0'>hvm</type>
            <boot dev='cdrom'/>
            <boot dev='hd'/>
          </os>
          <features>
            <acpi/>
            <apic/>
          </features>
          <cpu mode='host-passthrough' check='none'/>
          <clock offset='utc'/>
          <on_poweroff>destroy</on_poweroff>
          <on_reboot>restart</on_reboot>
          <on_crash>destroy</on_crash>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='/var/lib/libvirt/images/example-vm.qcow2'/>
              <target dev='vda' bus='virtio'/>
              <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
            </disk>
            <disk type='file' device='cdrom'>
              <driver name='qemu' type='raw'/>
              <source file='/var/lib/libvirt/images/ISOs/install.iso'/>
              <target dev='sda' bus='sata'/>
              <readonly/>
              <address type='drive' controller='0' bus='0' target='0' unit='0'/>
            </disk>
            <controller type='sata' index='0'>
              <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
            </controller>
            <interface type='network'>
              <mac address='52:54:00:00:00:01'/>
              <source network='default'/>
              <model type='virtio'/>
            </interface>
            <console type='pty'/>
            <graphics type='vnc' port='-1' autoport='yes'/>
            <video>
              <model type='virtio' heads='1' primary='yes'/>
            </video>
          </devices>
        </domain>
        EOF
      '';
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

