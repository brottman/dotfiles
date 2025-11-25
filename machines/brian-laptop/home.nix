{ config, pkgs, ... }:
{
  imports = [ ./obs-studio.nix ];
  # Required by Home Manager; set once and bump only after reading release notes.
  home.stateVersion = "25.05";
  
  # Autostart seafile-client
  systemd.user.services.seafile-client = {
    Unit = {
      Description = "Seafile Client";
      After = [ "graphical-session.target" ];
    };
    Service = {
      ExecStart = "${pkgs.seafile-client}/bin/seafile-applet";
      Restart = "on-failure";
    };
    Install = {
      WantedBy = [ "graphical-session.target" ];
    };
  };
  
  programs.plasma = {
    enable = true;
    workspace = {
      lookAndFeel = "org.kde.breezetwilight.desktop";
    };
    kscreenlocker = {
      autoLock = false;
    };
    configFile = {
      ksmserverrc = {
        General = {
          loginMode = "emptySession";
        };
      };
      taskmanagerrc = {
        Taskbar = {
          GroupingStrategy = 0;
        };
      };
      dolphinrc = {
        General = {
          ShowStatusBar = true;
        };
        "General/Toolbar" = {
          ToolBarIconSize = 0;
        };
        PreviewSettings = {
          Plugins = "appimagethumbnail,audiothumbnail,comicbookthumbnail,cursorthumbnail,djvuthumbnail,ebookthumbnail,exrthumbnail,imagethumbnail,jpegthumbnail,kraorathumbnail,ksvgthumbnail,networkstatusthumbnail,odfpreview,pdfthumbnail,plaintextpreview,svgthumbnail,tiffpreview,videothumbnail";
        };
        LocationBar = {
          PlacesPanel = true;
          Editable = true;
          ShowFullPath = true;
        };
      };
    };
    panels = [
      {
        location = "bottom";
        height = 45;
        floating = false;
      }
    ];
    powerdevil = {
      general = {
        pausePlayersOnSuspend = false;
      };
      AC = {
        autoSuspend.action = "nothing";
        powerButtonAction = "shutDown";
        whenLaptopLidClosed = "doNothing";
      };
      battery = {
        autoSuspend.action = "nothing";
        powerButtonAction = "shutDown";
        whenLaptopLidClosed = "turnOffScreen";
      };
      lowBattery = {
        autoSuspend.action = "nothing";
        powerButtonAction = "shutDown";
        whenLaptopLidClosed = "turnOffScreen";
      };
    };
  };

  programs.firefox = {
    enable = true;
    policies = {
      ExtensionSettings = {
        "{446900e4-71c2-419f-a6a7-df9c091e268b}" = {
          install_url = "https://addons.mozilla.org/firefox/downloads/latest/bitwarden-password-manager/latest.xpi";
          installation_mode = "force_installed";
        };
        "uBlock0@raymondhill.net" = {
          install_url = "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi";
          installation_mode = "force_installed";
        };
      };
    };
    profiles.brian = {
      isDefault = true;
      settings = {
        "identity.fxaccounts.account.device.name" = "brian-laptop";
      };
    };
  };

}
