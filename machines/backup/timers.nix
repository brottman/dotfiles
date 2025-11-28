# Systemd timers for backup machine maintenance tasks
{ config, pkgs, ... }:

{
    systemd.services.zfs-send-backup = {
        description = "ZFS send backup from superheavy";
        serviceConfig = {
            Type = "oneshot";
            User = "root";
        };
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/backup backpool/backup'';
    };
    systemd.timers.zfs-send-backup = {
        description = "Timer for ZFS backup sync";
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
            Unit = "zfs-send-backup.service";
        };
    };

    systemd.services.zfs-send-brian = {
        description = "ZFS send brian dataset from superheavy";
        serviceConfig = {
            Type = "oneshot";
            User = "root";
        };
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/brian backpool/brian'';
    };
    systemd.timers.zfs-send-brian = {
        description = "Timer for ZFS brian sync";
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
            Unit = "zfs-send-brian.service";
        };
    };    

    systemd.services.zfs-send-data = {
        description = "ZFS send data dataset from superheavy";
        serviceConfig = {
            Type = "oneshot";
            User = "root";
        };
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/data backpool/data'';
    };
    systemd.timers.zfs-send-data = {
        description = "Timer for ZFS data sync";
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
            Unit = "zfs-send-data.service";
        };
    };

    systemd.services.zfs-send-docker = {
        description = "ZFS send docker dataset from superheavy";
        serviceConfig = {
            Type = "oneshot";
            User = "root";
        };
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/docker backpool/docker'';
    };
    systemd.timers.zfs-send-docker = {
        description = "Timer for ZFS docker sync";
        wantedBy = [ "timers.target" ];
        timerConfig = {
            OnCalendar = "hourly";
            Persistent = true;
            Unit = "zfs-send-docker.service";
        };
    };
}
