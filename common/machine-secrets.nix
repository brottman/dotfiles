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
            description = "Authorized SSH public keys per user (format: ssh-ed25519 <key-material> <comment>)";
            example = {
              brian = [
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIJO8uo1P2tkol5uYYPtn/+SPp3xMUTPyuURcgsyg0jk brian@brian-laptop"
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJLMqTqjGGiFC8jjGi4hhXfk3mPz7ebJ8VJk5xaDmQb brian@superheavy"
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJM+DQTYuxIUkny90TbnL4xEfIN7jWzdhsFYkCDhePo brian@backup"
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILBVZabueeT2ESBtgz3blxhE39JQv736W0uDoZmRxP0D brian@docker"
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
      description = "Map of machine names to their SSH ed25519 host public key material (just the key, without 'ssh-ed25519' prefix)";
      example = {
        "brian-laptop" = "AAAAIIJO8uo1P2tkol5uYYPtn/+SPp3xMUTPyuURcgsyg0jk";
        "superheavy" = "AAAAIHJLMqTqjGGiFC8jjGi4hhXfk3mPz7ebJ8VJk5xaDmQb";
        "backup" = "AAAAIHJM+DQTYuxIUkny90TbnL4xEfIN7jWzdhsFYkCDhePo";
        "docker" = "AAAAILBVZabueeT2ESBtgz3blxhE39JQv736W0uDoZmRxP0D";
      };
    };
  };

  config = lib.mkMerge [
    (lib.mkIf cfg.enable {
      time.timeZone = cfg.timezone;
      environment.systemPackages = cfg.extraPackages;
    })

    # Apply SSH key configuration if enabled
    (lib.mkIf cfg.sshKeys.enable (
      let
        # Build authorized_keys per user
        authorizedKeysPerUser = lib.mapAttrs (userName: userKeys:
          userKeys ++ cfg.sshKeys.globalAuthorizedKeys
        ) cfg.sshKeys.authorizedKeys;
      in
      {
        # Set authorized keys for each user
        # Using foldl' to properly merge multiple user configurations
        users.users = lib.foldl' (acc: item:
          acc // {
            ${item.name} = {
              openssh.authorizedKeys.keys = item.keys;
            };
          }
        ) {}
        (lib.mapAttrsToList (name: keys: { inherit name keys; }) authorizedKeysPerUser);

        # Add trusted machines to known_hosts
        environment.etc."ssh/ssh_known_hosts".text = lib.concatStringsSep "\n"
          (lib.mapAttrsToList (name: key: "${name} ssh-ed25519 ${key}") cfg.trustedMachines)
          + "\n";
      }
    ))
  ];
}
