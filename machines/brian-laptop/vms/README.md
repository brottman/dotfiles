# Declarative VM Configuration Guide

This directory contains declaratively managed libvirt VM configurations for brian-laptop.

## Options for Declarative VM Management

### Option 1: Libvirt Domain XML Files + Systemd Services (Recommended)

**How it works:**
- Store VM domain XML files in this directory (e.g., `my-vm.xml`)
- Use systemd services in `configuration.nix` to automatically define VMs on boot
- Optionally auto-start VMs

**Pros:**
- Full control over VM configuration
- Version-controlled and reproducible
- Integrates with existing libvirt setup
- Can use `virsh dumpxml` to export existing VMs

**Cons:**
- Need to manage XML files manually
- More verbose configuration

### Option 2: Systemd Services with Inline virsh Commands

**How it works:**
- Define VMs directly in systemd services using virsh commands
- Can include disk creation, network setup, etc.

**Pros:**
- Everything in Nix configuration
- Can use Nix variables and functions

**Cons:**
- Less flexible than XML
- Harder to modify complex VM configs

### Option 3: Extend manage.py Script

**How it works:**
- Add functionality to `manage.py` to generate and manage VM configs
- Could generate XML files or systemd services automatically

**Pros:**
- Interactive wizard (already exists)
- Could automate common VM types

**Cons:**
- Less "declarative" - more imperative
- Requires Python script maintenance

## Example: Creating a Declarative VM

### Step 1: Export existing VM (if you have one)

```bash
virsh dumpxml my-vm > machines/brian-laptop/vms/my-vm.xml
```

### Step 2: Edit the XML (optional)

You may want to:
- Adjust resource allocation (CPU, memory)
- Change disk paths
- Update network settings
- Add/remove devices

### Step 3: Add systemd service to configuration.nix

```nix
# Define the VM domain
systemd.services.define-vm-myvm = {
  description = "Define VM: myvm";
  after = [ "libvirtd.service" ];
  requires = [ "libvirtd.service" ];
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStart = "${pkgs.libvirt}/bin/virsh define ${./vms/my-vm.xml}";
  };
  wantedBy = [ "multi-user.target" ];
};

# Optionally auto-start the VM on boot
systemd.services.autostart-vm-myvm = {
  description = "Autostart VM: myvm";
  after = [ "define-vm-myvm.service" "libvirtd.service" ];
  requires = [ "define-vm-myvm.service" ];
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStart = "${pkgs.libvirt}/bin/virsh autostart myvm";
  };
  wantedBy = [ "multi-user.target" ];
};
```

### Step 4: Rebuild

```bash
sudo nixos-rebuild switch
```

## Using the Helper Function

For multiple VMs, you can create a helper function in `configuration.nix`:

```nix
# Helper function to define a VM
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

# Then use it:
systemd.services.define-vm-myvm = defineVM "my-vm";
systemd.services.define-vm-another = defineVM "another-vm";
```

## Managing VMs

- **List VMs:** `virsh list --all`
- **Start VM:** `virsh start my-vm`
- **Stop VM:** `virsh shutdown my-vm` (graceful) or `virsh destroy my-vm` (force)
- **View console:** `virsh console my-vm`
- **Edit XML:** `virsh edit my-vm` (then export to file)
- **Undefine VM:** `virsh undefine my-vm` (removes from libvirt, doesn't delete disk)

## Notes

- VM disk images are typically stored outside this repo (e.g., `/data/vms/`)
- XML files should only contain the domain definition, not disk images
- Changes to XML files require rebuild to take effect
- You can use `virsh edit` to modify running VMs, but changes won't persist across reboots unless you export them back to the XML file

