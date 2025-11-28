NixOS VM modules (built-in) using virtualisation.* modules



The VM will be automatically defined when you rebuild your NixOS configuration. After rebuilding, you can:
Start the VM: virsh start guestvm
Stop the VM: virsh shutdown guestvm
View VM status: virsh list --all
Connect to console: virsh console guestvm