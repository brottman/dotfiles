# Examples: How to integrate declarative VMs into configuration.nix
# Copy the relevant sections into your machines/brian-laptop/configuration.nix

# ============================================================================
# OPTION 1: Individual VM Services (Simple, explicit)
# ============================================================================

# Define a single VM
systemd.services.define-vm-example = {
  description = "Define VM: example-vm";
  after = [ "libvirtd.service" ];
  requires = [ "libvirtd.service" ];
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStart = "${pkgs.libvirt}/bin/virsh define ${./vms/example-vm.xml}";
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

# ============================================================================
# OPTION 2: Helper Function + List (Scalable, clean)
# ============================================================================

# Add this helper function (best placed near the top of your config, 
# inside the main configuration block or as a let binding)

let
  # Helper function to define a VM domain
  defineVM = name: {
    description = "Define VM: ${name}";
    after = [ "libvirtd.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./vms/${name}.xml}";
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
  managedVMs = [ "example-vm" "another-vm" ];
  autoStartVMs = [ "example-vm" ];  # Only auto-start specific VMs

in {
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

# ============================================================================
# OPTION 3: Using lib.attrsets (Advanced, NixOS-style)
# ============================================================================

# More NixOS-idiomatic approach using lib.mkMerge
systemd.services = lib.mkMerge [
  # ... your existing services ...
  
  # VM definitions
  (lib.genAttrs [ "example-vm" "another-vm" ] (name: {
    description = "Define VM: ${name}";
    after = [ "libvirtd.service" ];
    requires = [ "libvirtd.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.libvirt}/bin/virsh define ${./vms/${name}.xml}";
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

# ============================================================================
# OPTION 4: Full VM with Disk Creation (Advanced)
# ============================================================================

# If you also want to create/manage disk images declaratively
systemd.services.create-vm-disk-example = {
  description = "Create disk image for example-vm";
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p /data/vms";
    ExecStart = "${pkgs.qemu}/bin/qemu-img create -f qcow2 /data/vms/example-vm.qcow2 20G";
  };
  wantedBy = [ "multi-user.target" ];
  before = [ "define-vm-example.service" ];
};

# ============================================================================
# NOTES:
# ============================================================================
# 
# 1. Replace "example-vm" with your actual VM name
# 2. Ensure the XML file path matches: ./vms/your-vm-name.xml
# 3. Auto-start services should come AFTER define services
# 4. Use `virsh dumpxml existing-vm` to export existing VMs
# 5. After adding config, rebuild: sudo nixos-rebuild switch
# 6. Check status: systemctl status define-vm-example
# 7. List VMs: virsh list --all

