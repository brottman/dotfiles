Great! You have several themes available. Here are the interesting ones:

bgrt (current) - BIOS/UEFI background replacement
details - Shows boot details/messages in real-time
spinner - Simple spinning animation
spinfinity - Infinity symbol spinner
glow - Glowing animation
solar - Solar system animation
tribar - Three-bar loading animation
fade-in - Simple fade-in effect
text - Text-based (shows messages)
For what you want (animation with kernel messages visible), the best options are:

details - This is specifically designed to show boot messages while an animation plays
text - Simple text output of kernel messages
Let me update your configuration to use the details theme, which will show kernel messages in a smaller area while displaying a nice animation:


Use plasma-manager to update the configuration for brian-laptop. I want the global theme to be set "Breeze Twilight", the panel to have a height of 45, and the panel to not float. I also want the power button to always immediately "Shut Down", and for the machine to never sleep.



Current Setup
Your laptop uses Plymouth with the "tribar" theme plus quiet boot parameters. Here are other approaches:

Alternatives:
Custom GRUB Themes (if using GRUB bootloader)

Customize boot.loader.grub with theme, background, and font settings
Not applicable to your systemd-boot, but worth knowing
systemd-boot Customization (your current bootloader)

Modify boot.loader.systemd-boot settings
Set custom background images and titles
Limited compared to GRUB but cleaner
EarlyOOM/systemd Splash

Use systemd's built-in splash screen
Lighter than Plymouth, no additional service needed
EFISTUB Direct Boot

Boot directly from kernel without bootloader splash
Minimal visual feedback
Kernel Framebuffer Splash

Use kernel's native framebuffer splash feature
Requires specific kernel parameters and PSF font files
Custom initrd Message

Display custom text during boot via boot.initrd.preFailureCommands
Very minimal approach
Bootsplash (newer alternative to Plymouth)

Modern splash screen system
Less widely used in NixOS but available
No Splash - Just Clean Terminal

Remove "splash" from boot.kernelParams
Keep "quiet" for cleaner boot
Most minimal approach
Recommendation:
If you want something lighter than Plymouth, try disabling Plymouth and using clean systemd boot with minimal kernel params:





For Power Management, want:

On AC Power
    When inactive: Do nothing
    When power button pressed: Shut down
    When laptop lid closed: Do nothing

On Battery
    When inactive: Do nothing
    When power button pressed: Shut down
    When laptop lid closed: Turn off screen

On Low Battery
    When inactive: Do nothing
    When power button pressed: Shut down
    When laptop lid closed: Turn off screen