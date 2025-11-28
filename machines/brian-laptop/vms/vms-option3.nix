# Option 3: Using lib.attrsets (Advanced, NixOS-style)
# This approach uses lib.genAttrs and lib.mkMerge for a more NixOS-idiomatic style
# Best for: NixOS veterans, integration with existing complex configurations
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

  # Merge VM services with existing systemd services
  systemd.services = lib.mkMerge [
    # ... your existing services would go here ...
    
    # VM definitions
    (lib.genAttrs [ "example-vm" "another-vm" "third-vm" ] (name: {
      description = "Define VM: ${name}";
      after = [ "libvirtd.service" ];
      requires = [ "libvirtd.service" ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${pkgs.libvirt}/bin/virsh define ${./${name}.xml}";
      };
      wantedBy = [ "multi-user.target" ];
    }))
    
    # VM auto-starts
    (lib.genAttrs [ "example-vm" ] (name: {
      description = "Autostart VM: ${name}";
      after = [ "define-vm-${name}.service" "libvirtd.service" ];
      requires = [ "define-vm-${name}.service" ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${pkgs.libvirt}/bin/virsh autostart ${name}";
      };
      wantedBy = [ "multi-user.target" ];
    }))
  ];
}

