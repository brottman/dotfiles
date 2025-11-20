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
  };

  config = lib.mkIf cfg.enable {
    time.timeZone = cfg.timezone;
    environment.systemPackages = cfg.extraPackages;
  };
}
