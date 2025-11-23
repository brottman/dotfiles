# Systemd timers for backup machine maintenance tasks
{ config, pkgs, ... }:

{
    systemd.services.zfs-send-backup = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/backup backpool/backup >> /root/systemd.log'';
    };
    systemd.timers.zfs-send-backup = {
        wantedBy = [ "timers.target" ];
        partOf = [ "zfs-send-backup.service" ];
        timerConfig = {
        OnCalendar = "hourly";
        Unit = "zfs-send-backup.service";
        };
    };

    systemd.services.zfs-send-brian = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/brian backpool/brian >> /root/systemd.log'';
    };
    systemd.timers.zfs-send-brian = {
        wantedBy = [ "timers.target" ];
        partOf = [ "zfs-send-brian.service" ];
        timerConfig = {
        OnCalendar = "hourly";
        Unit = "zfs-send-brian.service";
        };
    };    

    systemd.services.zfs-send-data = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/data backpool/data >> /root/systemd.log'';
    };
    systemd.timers.zfs-send-data = {
        wantedBy = [ "timers.target" ];
        partOf = [ "zfs-send-data.service" ];
        timerConfig = {
        OnCalendar = "hourly";
        Unit = "zfs-send-data.service";
        };
    };

    systemd.services.zfs-send-docker = {
        serviceConfig.Type = "oneshot";
        path = with pkgs; [ bash ];
        script = ''${pkgs.sanoid}/bin/syncoid -r --delete-target-snapshots superheavy:datapool/docker backpool/docker >> /root/systemd.log'';
    };
    systemd.timers.zfs-send-docker = {
        wantedBy = [ "timers.target" ];
        partOf = [ "zfs-send-docker.service" ];
        timerConfig = {
        OnCalendar = "hourly";
        Unit = "zfs-send-docker.service";
        };
    };
}
