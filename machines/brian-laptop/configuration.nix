# Laptop machine configuration
{ config, pkgs, lib, ... }:

{
  imports = [
    ../../common/common.nix
  ];

  # Allow unfree packages
  nixpkgs.config.allowUnfree = true;

  # Allow insecure packages
  nixpkgs.config.permittedInsecurePackages = [ "ventoy-1.1.07" ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Use latest kernel
  boot.kernelPackages = pkgs.linuxPackages_latest;

  # Enable bcachefs support
  boot.supportedFilesystems = [ "bcachefs" ];

  # Boot configuration
  boot.initrd.kernelModules = [ ];

  # Quiet boot
  boot.kernelParams = [
    "quiet"
    "loglevel=3"
  ];
  boot.consoleLogLevel = 0;
  boot.initrd.verbose = false;

  # Networking
  networking.hostName = "brian-laptop";
  networking.networkmanager.enable = true;

  # Graphics (Intel integrated + NVIDIA)
  services.xserver = {
    enable = true;
    videoDrivers = [ "nvidia" ];
  };
  services.desktopManager.plasma6.enable = true;
  services.displayManager.sddm.enable = true;
  services.displayManager.sddm.wayland.enable = true;
  
  # Disable KDE Plasma's power button handler
  environment.etc."xdg/kdedefaults/powermanagementrc".text = ''
    [General]
    powerButtonAction=0
  '';
  services.displayManager.autoLogin = {
    enable = true;
    user = "brian";
  };

  # Intel graphics
  hardware.graphics = {
    enable = true;
  };

  # NVIDIA graphics
  hardware.nvidia = {
    modesetting.enable = true;
    powerManagement.enable = true;
    powerManagement.finegrained = true;
    prime.offload.enable = true;
    prime.intelBusId = "PCI:0:2:0";
    prime.nvidiaBusId = "PCI:1:0:0";
    package = config.boot.kernelPackages.nvidiaPackages.production;
    open = false;
    nvidiaSettings = true;
  };

  # Power management for laptop
  services.power-profiles-daemon.enable = false;
  services.tlp = {
    enable = true;
    settings = {
      CPU_SCALING_GOVERNOR_ON_AC = "performance";
      CPU_SCALING_GOVERNOR_ON_BAT = "powersave";
      ENERGY_PERF_POLICY_ON_AC = "performance";
      ENERGY_PERF_POLICY_ON_BAT = "power";
    };
  };

  # Disable sleep/suspend
  systemd.sleep.extraConfig = ''
    [Sleep]
    AllowSuspend=no
    AllowHibernation=no
    AllowSuspendThenHibernate=no
    AllowHybridSleep=no
  '';

  # Disable screen blanking
  services.xserver.serverFlagsSection = ''
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
  '';

  # Power button action
  services.logind.settings = {
    Login = {
      HandlePowerKey = "reboot";
      HandlePowerKeyLongPress = "poweroff";
    };
  };

  # Sound
  services.pulseaudio.enable = false;
  services.pipewire = {
    enable = true;
    pulse.enable = true;
    alsa.enable = true;
  };

  # Bluetooth
  hardware.bluetooth = {
    enable = true;
    powerOnBoot = true;
  };
  #services.blueman.enable = true;

  # Trackpad
  services.libinput = {
    enable = true;
    touchpad = {
      naturalScrolling = true;
      tapping = true;
    };
  };

  # Steam
  programs.steam = {
    enable = true;
    remotePlay.openFirewall = true;
    dedicatedServer.openFirewall = true;
  };


  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 80 443 ];
    allowedUDPPorts = [ ];
  };

  # Nginx web server
  services.nginx = {
    enable = true;
    virtualHosts = {
      "localhost" = {
        root = "/home/brian/html";
        listen = [
          { addr = "0.0.0.0"; port = 80; }
        ];
        locations."/".extraConfig = "autoindex on;";
      };
    };
  };

  # Ollama
  services.ollama = {
    enable = true;
    acceleration = "cuda";
  };

  # Virtualisation: libvirtd for VM management
  virtualisation.libvirtd = {
    enable = true;
    qemu = {
      package = pkgs.qemu_kvm;
      swtpm.enable = true;
    };
  };

  # Add user to libvirt group for VM management
  # NixOS automatically merges extraGroups from multiple modules
  users.users.brian.extraGroups = [ "libvirtd" ];

  # Declarative VM: guestvm
  # Create ISOs directory for storage pool
  systemd.services.create-isos-directory = {
    description = "Create ISOs directory for libvirt storage pool";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.coreutils}/bin/mkdir -p /var/lib/libvirt/images/ISOs";
    };
    wantedBy = [ "multi-user.target" ];
    before = [ "define-vm-guestvm.service" ];
  };

  # Create disk image if it doesn't exist
  systemd.services.create-guestvm-disk = {
    description = "Create disk image for guestvm";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p /var/lib/libvirt/images";
      ExecStart = "${pkgs.qemu}/bin/qemu-img create -f qcow2 /var/lib/libvirt/images/guestvm.qcow2 20G";
    };
    wantedBy = [ "multi-user.target" ];
    before = [ "define-vm-guestvm.service" ];
    unitConfig.ConditionPathExists = "!/var/lib/libvirt/images/guestvm.qcow2";
  };

  # Define the VM domain
  systemd.services.define-vm-guestvm = {
    description = "Define VM: guestvm";
    after = [ "libvirtd.service" "create-guestvm-disk.service" ];
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
          <memory unit='KiB'>1048576</memory>
          <currentMemory unit='KiB'>1048576</currentMemory>
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
              <source file='/var/lib/libvirt/images/guestvm.qcow2'/>
              <target dev='vda' bus='virtio'/>
              <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
            </disk>
            <disk type='file' device='cdrom'>
              <driver name='qemu' type='raw'/>
              <source file='/data/Seafile/ISOs/nixos-minimal-25.05.812880.4c8cdd5b1a63-x86_64-linux.iso'/>
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

  # Additional packages for laptop
  environment.systemPackages = with pkgs; [
    anki
    bluez
    bluez-tools
    google-chrome
    code-cursor
    devenv
    dtrx # file extractor
    exiftool
    ffmpeg
    filezilla
    fsearch
    gimp
    gocryptfs
    joplin-desktop
    lmstudio
    lutris
    opencode
    pinta
    prismlauncher
    python3
    rclone
    remmina
    restic
    rustdesk
    shellcheck
    seafile-client
    srm
    thunderbird
    qbittorrent
    scrcpy
    gzdoom
    ventoy
    virt-manager
    vlc
    vscode-fhs
    wine
    zoom-us
  ];

  # Environment variables
  environment.variables = {
    # Add environment variables here
  };

  # Environment aliases
  environment.shellAliases = {
    update = "sudo sh ~/dotfiles/manage-nixos.sh switch";
    gc = "sudo sh ~/dotfiles/manage-nixos.sh switch";
    ff = "fastfetch";
    lock = "sudo umount /data/archive/plain";
    #unlock = "sudo mount /dev/disk/by-uuid/04966b6f-b27c-4b47-a589-c3243e9a03bf /data/archive/plain";
    unlock = "gocryptfs /data/archive/cipher/ /data/archive/plain/";
    clean = "srm -rfv /home/brian/.cache/thumbnails/;
            srm -rfv /home/brian/.config/gthumb/history.xbel;
            srm -rfv /home/brian/.config/gwenviewrc;
            srm -rfv /home/brian/.config/vlc/vlc-qt-interface.conf;
            srm -rfv '/home/brian/.tor project/';
            srm -rfv '/home/brian/.cache/tor project/';
            srm -rfv '/home/brian/.tor project/';";
    reboot = "sudo systemctl reboot";
    shutdown = "sudo systemctl poweroff";
    comfyui = "python /data/archive/ComfyUI/main.py";
    comfyui89 = "python /data/archive/plain/ComfyUI/main.py";
  };

  # System state version (override common default)
  system.stateVersion = "25.05";
}
