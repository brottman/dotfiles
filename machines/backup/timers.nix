# Systemd timers for backup machine maintenance tasks
{ config, pkgs, ... }:

{
    systemd.services.zfs-send-backup = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/backup backpool/backup'';
    };
    systemd.timers.zfs-send-backup = {
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
        };
    };

    systemd.services.zfs-send-brian = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/brian backpool/brian'';
    };
    systemd.timers.zfs-send-brian = {
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
        };
    };    

    systemd.services.zfs-send-data = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/data backpool/data'';
    };
    systemd.timers.zfs-send-data = {
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
        };
    };

    systemd.services.zfs-send-docker = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/docker backpool/docker'';
    };
    systemd.timers.zfs-send-docker = {
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
        };
    };
}
