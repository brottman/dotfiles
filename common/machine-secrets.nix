# Optional module for machine-specific secrets and overrides
# Import this in specific machine configurations as needed

{ config, lib, pkgs, ... }:

let
  cfg = config.machine-secrets;
in

{
  options.machine-secrets = {
    enable = lib.mkEnableOption "machine-specific secrets and overrides";
    
    wifiSSID = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "WiFi SSID for this machine";
    };
    
    timezone = lib.mkOption {
      type = lib.types.str;
      default = "UTC";
      description = "Timezone for this machine";
    };
    
    extraPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [];
      description = "Extra packages to install on this machine";
    };

    # SSH key management
    sshKeys = lib.mkOption {
      type = lib.types.submodule {
        options = {
          enable = lib.mkEnableOption "SSH key management";
          
          # Host SSH public key (for other machines to trust this one)
          hostPublicKey = lib.mkOption {
            type = lib.types.str;
            default = "";
            description = "SSH host public key (ed25519 format). Leave empty to skip.";
          };
          
          # SSH keys authorized for specific users
          authorizedKeys = lib.mkOption {
            type = lib.types.attrsOf (lib.types.listOf lib.types.str);
            default = {};
            description = "Authorized SSH public keys per user (e.g., { brian = [\"ssh-ed25519 ...\"]; })";
            example = {
              brian = [
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKey1 brian@laptop"
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKey2 brian@server"
              ];
            };
          };

          # Global authorized keys (added to all users)
          globalAuthorizedKeys = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [];
            description = "SSH public keys authorized for all users";
          };
        };
      };
      default = { enable = false; };
      description = "SSH key configuration for inter-machine trust";
    };

    # Inter-machine trust configuration
    trustedMachines = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = {};
      description = "Map of machine names to their SSH host public keys for SSH known_hosts";
      example = {
        "superheavy" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleHostKey1 superheavy";
        "docker" = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleHostKey2 docker";
      };
    };
  };

  config = lib.mkMerge [
    (lib.mkIf cfg.enable {
      time.timeZone = cfg.timezone;
      environment.systemPackages = cfg.extraPackages;
    })

    # Apply SSH key configuration if enabled
    (lib.mkIf cfg.sshKeys.enable {
      # Set authorized keys for users
      users.users = lib.mapAttrs (userName: userKeys:
        {
          openssh.authorizedKeys.keys = 
            userKeys ++ cfg.sshKeys.globalAuthorizedKeys;
        }
      ) cfg.sshKeys.authorizedKeys;

      # Add trusted machines to known_hosts
      environment.etc."ssh/ssh_known_hosts".text = lib.concatStringsSep "\n"
        (lib.mapAttrsToList (name: key: "${name} ${key}") cfg.trustedMachines);
    })
  ];
}
