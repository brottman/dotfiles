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
    before = [ "create-vm-disk-guestvm.service" ];
  };

  # Create disk image if it doesn't exist
  systemd.services.create-vm-disk-guestvm = {
    description = "Create disk image for guestvm";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p /data/VMs";
      ExecStart = "${pkgs.qemu}/bin/qemu-img create -f qcow2 /data/VMs/guestvm.qcow2 64G";
    };
    wantedBy = [ "multi-user.target" ];
    before = [ "define-vm-guestvm.service" ];
    unitConfig.ConditionPathExists = "!/data/VMs/guestvm.qcow2";
  };

  # Define the VM domain with inline XML
  systemd.services.define-vm-guestvm = {
    description = "Define VM: guestvm";
    after = [ "libvirtd.service" "create-vm-disk-guestvm.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = pkgs.writeShellScript "define-guestvm" ''
        # Undefine the VM if it already exists (idempotent operation)
        # This allows the configuration to be updated without manual intervention
        if ${pkgs.libvirt}/bin/virsh dominfo guestvm &>/dev/null; then
          ${pkgs.libvirt}/bin/virsh undefine guestvm || true
        fi
        
        # Define the VM
        ${pkgs.libvirt}/bin/virsh define /dev/stdin <<EOF
        <domain type='kvm'>
          <name>guestvm</name>
          <memory unit='KiB'>8388608</memory>
          <currentMemory unit='KiB'>8388608</currentMemory>
          <vcpu placement='static'>4</vcpu>
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
              <source file='/data/VMs/guestvm.qcow2'/>
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
  systemd.services.autostart-vm-guestvm = {
    description = "Autostart VM: guestvm";
    after = [ "define-vm-guestvm.service" "libvirtd.service" ];
    requires = [ "define-vm-guestvm.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh autostart guestvm";
    };
    wantedBy = [ "multi-user.target" ];
  };
}

