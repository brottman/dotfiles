#!/bin/sh
#
# For installing NixOS having booted from the minimal USB image.
#
# To run:
#
#     sh -c "$(curl https://eipi.xyz/nixinst.sh)"
#
# https://eipi.xyz/blog/nixos-x86-64

echo "--------------------------------------------------------------------------------"
echo "Your attached storage devices will now be listed."
read -p "Press 'q' to exit the list. Press enter to continue." NULL

sudo fdisk -l | less

echo "--------------------------------------------------------------------------------"
echo "Detected the following devices:"
echo

i=0
for device in $(sudo fdisk -l | grep "^Disk /dev" | awk "{print \$2}" | sed "s/://"); do
    echo "[$i] $device"
    i=$((i+1))
    DEVICES[$i]=$device
done

echo
read -p "Which device do you wish to install on? " DEVICE

DEV=${DEVICES[$(($DEVICE+1))]}

read -p "Will now partition ${DEV}. Ok? Type 'go': " ANSWER

if [ "$ANSWER" = "go" ]; then
    echo "partitioning ${DEV}..."
    (
      echo g # new gpt partition table

      echo n # new partition
      echo 2 # partition 2
      echo   # default start sector
      echo +512M # size is 512M

      echo n # new partition
      echo 1 # first partition
      echo   # default start sector
      echo   # default end sector

      echo t # set type
      echo 1 # first partition
      echo 20 # Linux Filesystem

      echo t # set type
      echo 2 # second partition
      echo 1 # EFI System

      echo p # print layout

      echo w # write changes
    ) | sudo fdisk ${DEV}
else
    echo "cancelled."
    exit
fi

echo "--------------------------------------------------------------------------------"
echo "checking partition alignment..."

function align_check() {
    (
      echo
      echo $1
    ) | sudo parted $DEV align-check | grep aligned | sed "s/^/partition /"
}

align_check 1
align_check 2

echo "--------------------------------------------------------------------------------"
echo "getting created partition names..."

i=1
for part in $(sudo fdisk -l | grep $DEV | grep -v "," | awk '{print $1}'); do
    echo "[$i] $part"
    i=$((i+1))
    PARTITIONS[$i]=$part
done

P1=${PARTITIONS[2]}
P2=${PARTITIONS[3]}

echo "--------------------------------------------------------------------------------"
read -p "Press enter to install NixOS." NULL

echo "making filesystem on ${P1}..."

sudo mkfs.ext4 -L nixos ${P1}

echo "making filesystem on ${P2}..."

sudo mkfs.fat -F 32 -n boot ${P2}            # (for UEFI systems only)

echo "mounting filesystems..."

sudo mount /dev/disk/by-label/nixos /mnt
sudo mkdir -p /mnt/boot                      # (for UEFI systems only)
sudo mount /dev/disk/by-label/boot /mnt/boot # (for UEFI systems only)

echo "generating NixOS configuration..."

sudo nixos-generate-config --root /mnt

echo "configuring bootloader for UEFI (systemd-boot)..."

# Remove any existing bootloader configuration lines
sudo sed -i '/boot.loader.systemd-boot.enable = /d' /mnt/etc/nixos/configuration.nix
sudo sed -i '/boot.loader.grub.enable = /d' /mnt/etc/nixos/configuration.nix
sudo sed -i '/boot.loader.grub.devices = /d' /mnt/etc/nixos/configuration.nix
sudo sed -i '/boot.loader.efi.canTouchEfiVariables = /d' /mnt/etc/nixos/configuration.nix

# Add bootloader configuration using a temporary file
sudo sh -c 'cat >> /mnt/etc/nixos/configuration.nix << EOF

  # Bootloader (configured for UEFI)
  boot.loader.grub.enable = false;
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
EOF
'

read -p "Press enter and the Nix configuration will be opened in nano."

sudo nano /mnt/etc/nixos/configuration.nix

echo "installing NixOS..."

sudo nixos-install

read -p "Remove installation media and press enter to reboot." NULL

reboot