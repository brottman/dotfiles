# VM Management Options

This directory contains 5 different approaches for managing virtual machines (VMs) with libvirt in NixOS. Each option has different trade-offs in terms of simplicity, scalability, and maintainability.

## Overview

All options share the same base configuration:
- Enable `libvirtd` for VM management
- Configure QEMU/KVM with TPM support (swtpm)
- Add user to `libvirtd` group for VM management permissions

The differences lie in how VMs are defined and managed.

## Option 1: Individual VM Services (Simple, explicit)

**File:** `vms-option1.nix`

**Best for:** Small number of VMs, maximum clarity

**Description:**
This is the simplest approach where each VM is defined as a separate systemd service. Each VM gets its own `define-vm-*` service that runs `virsh define` on an external XML file. Optionally, you can add `autostart-vm-*` services to automatically start VMs on boot.

**Pros:**
- Very explicit and easy to understand
- Easy to see what each VM does
- Simple to add or remove individual VMs

**Cons:**
- Repetitive code when managing many VMs
- Not scalable for large numbers of VMs

**Example:**
- Defines `example-vm` using `example-vm.xml`
- Optionally auto-starts `example-vm` on boot
- Can easily add more VMs by duplicating the service definitions

---

## Option 2: Helper Function + List (Scalable, clean)

**File:** `vms-option2.nix`

**Best for:** Multiple VMs, maintainable and DRY (Don't Repeat Yourself)

**Description:**
This approach uses helper functions (`defineVM` and `autostartVM`) to generate systemd services for multiple VMs from a list. You define your VMs in a list (`managedVMs`) and optionally specify which ones should auto-start (`autoStartVMs`).

**Pros:**
- DRY - no code duplication
- Easy to add/remove VMs by modifying lists
- Scales well to many VMs
- Clean separation of concerns

**Cons:**
- Slightly more complex than Option 1
- Requires understanding of Nix list operations

**Example:**
- `managedVMs = [ "example-vm" "another-vm" "third-vm" ]`
- `autoStartVMs = [ "example-vm" ]`
- Automatically generates all necessary services

---

## Option 3: Using lib.attrsets (Advanced, NixOS-style)

**File:** `vms-option3.nix`

**Best for:** NixOS veterans, integration with existing complex configurations

**Description:**
This approach uses NixOS library functions (`lib.genAttrs` and `lib.mkMerge`) for a more idiomatic NixOS style. It's similar to Option 2 but uses NixOS-specific utilities that integrate better with complex configurations.

**Pros:**
- Most NixOS-idiomatic approach
- Integrates well with existing complex configurations
- Can easily merge with other systemd services using `lib.mkMerge`

**Cons:**
- Requires familiarity with NixOS library functions
- More abstract than Options 1 and 2

**Example:**
- Uses `lib.genAttrs` to generate services from a list
- Uses `lib.mkMerge` to merge with existing services
- Same VM list approach as Option 2

---

## Option 4: Full VM with Disk Creation (Advanced)

**File:** `vms-option4.nix`

**Best for:** Complete declarative VM management including storage

**Description:**
This option extends Option 1 by adding disk image creation as part of the VM definition. It creates the disk image using `qemu-img` before defining the VM, making the entire VM lifecycle declarative.

**Pros:**
- Complete declarative management including storage
- Automatically creates disk images if they don't exist
- Creates necessary directories (e.g., ISOs directory)
- Idempotent - safe to run multiple times

**Cons:**
- More complex than Options 1-3
- Still requires external XML files
- More services to manage

**Example:**
- Creates `/var/lib/libvirt/images/ISOs` directory
- Creates `example-vm.qcow2` disk image (20GB) if it doesn't exist
- Defines the VM using `example-vm.xml`
- Optionally auto-starts the VM

---

## Option 5: Inline XML in Systemd Service

**File:** `vms-option5.nix`

**Best for:** Everything in Nix, no external XML files needed

**Description:**
This is the most self-contained option. It defines the VM XML directly in the systemd service using a shell script with a heredoc. It also includes disk creation like Option 4, but everything is in one Nix file.

**Pros:**
- No external XML files needed
- Everything is in Nix
- Includes disk creation
- Idempotent - automatically undefines existing VM before redefining
- Most self-contained option

**Cons:**
- XML embedded in Nix can be harder to read/edit
- Less flexible for complex XML editing
- Most complex option

**Example:**
- Creates directories and disk images (like Option 4)
- Defines VM with inline XML using shell script heredoc
- Automatically handles VM redefinition (undefines if exists)
- Includes full VM configuration: memory, CPU, disks, network, graphics, etc.

---

## Comparison Table

| Option | Complexity | Scalability | External Files | Disk Management | Best For |
|--------|-----------|-------------|----------------|-----------------|----------|
| 1      | Low       | Low         | Yes (XML)      | No              | Small setups |
| 2      | Medium    | High        | Yes (XML)      | No              | Multiple VMs |
| 3      | Medium    | High        | Yes (XML)      | No              | NixOS experts |
| 4      | Medium    | Low         | Yes (XML)      | Yes             | Complete control |
| 5      | High      | Medium      | No             | Yes             | Self-contained |

## Usage

To use any of these options, import the desired file in your `configuration.nix`:

```nix
imports = [
  ./vms/vms-option1.nix  # or option2, option3, option4, or option5
];
```

## Example VM XML

The `example-vm.xml` file provides a template for VM definitions. You can:
- Customize it for your needs
- Export from an existing VM: `virsh dumpxml vm-name > example-vm.xml`
- Use it as a starting point for new VMs

## Notes

- All options require the user to be in the `libvirtd` group (handled automatically)
- All options use `libvirtd` service which must be running
- Auto-start services are optional - remove them if you don't want VMs to start on boot
- Disk images in Option 4 and 5 are created with `ConditionPathExists` to avoid overwriting existing disks
- Option 5 automatically handles VM redefinition by undefining existing VMs first

