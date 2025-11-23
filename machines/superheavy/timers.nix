# Systemd timers for superheavy server
{ config, pkgs, ... }:

{
  # ZFS Scrub Monitoring
  systemd.services.zfs-scrub-monitor = {
    description = "Monitor ZFS pool health and send email reports";
    script = ''
      #!/bin/bash
      TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
      REPORT="/tmp/zfs-scrub-report-$$.txt"
      
      {
        echo "ZFS Pool Health Report - $TIMESTAMP"
        echo "=================================="
        echo ""
        
        # Get pool status
        ${pkgs.zfs}/bin/zpool status
        echo ""
        
        # Get scrub status
        echo "Recent Scrub History:"
        echo "---"
        ${pkgs.zfs}/bin/zpool status | grep -A 5 "scrub"
        echo ""
        
        # Check for any errors
        ERRORS=$(${pkgs.zfs}/bin/zpool status | grep -c "DEGRADED\|FAULTED\|OFFLINE")
        if [ "$ERRORS" -gt 0 ]; then
          echo "⚠️  ALERT: Pool has errors or degraded status!"
        else
          echo "✓ All pools healthy"
        fi
      } > "$REPORT"
      
      # Send email report
      {
        echo "From: root@superheavy"
        echo "To: brottman@gmail.com"
        echo "Subject: ZFS Scrub Report - $(hostname) - $TIMESTAMP"
        echo ""
        cat "$REPORT"
      } | ${pkgs.msmtp}/bin/msmtp brottman@gmail.com
      
      # Cleanup
      rm -f "$REPORT"
    '';
    serviceConfig = {
      Type = "oneshot";
      User = "root";
    };
  };

  systemd.timers.zfs-scrub-monitor = {
    description = "Timer for ZFS pool monitoring";
    timerConfig = {
      # Run weekly on Sunday at 2 AM
      OnCalendar = "Sun *-*-* 02:00:00";
      Persistent = true;
      Unit = "zfs-scrub-monitor.service";
    };
    wantedBy = [ "timers.target" ];
  };

  # Service Failure Notifications
  systemd.services.service-failure-handler = {
    description = "Send email notification for service failures";
    serviceConfig = {
      Type = "oneshot";
      User = "root";
      ExecStart = ''
        ${pkgs.bash}/bin/bash -c '
          SERVICE_NAME="%n"
          HOSTNAME=$(hostname)
          TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
          
          {
            echo "Service Failure Alert"
            echo "===================="
            echo ""
            echo "Hostname: $HOSTNAME"
            echo "Timestamp: $TIMESTAMP"
            echo "Service: $SERVICE_NAME"
            echo ""
            echo "Service Status:"
            systemctl status "$SERVICE_NAME" || true
            echo ""
            echo "Recent Logs:"
            journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true
          } | ${pkgs.bash}/bin/bash -c "{ echo 'From: root@superheavy'; echo 'To: brottman@gmail.com'; echo 'Subject: ALERT: Service Failed on $HOSTNAME - $SERVICE_NAME'; echo ''; cat; } | ${pkgs.msmtp}/bin/msmtp brottman@gmail.com"
        '
      '';
    };
  };

  # Monitoring service to check critical services are running
  systemd.services.critical-service-monitor = {
    description = "Monitor critical services and alert if down";
    script = ''
      #!/bin/bash
      CRITICAL_SERVICES=("samba" "postfix" "docker" "zfs-scrub-monitor.timer")
      FAILED_SERVICES=()
      HOSTNAME=$(hostname)
      TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
      
      for service in "''${CRITICAL_SERVICES[@]}"; do
        if ! systemctl is-active --quiet "$service" 2>/dev/null; then
          FAILED_SERVICES+=("$service")
        fi
      done
      
      if [ ''${#FAILED_SERVICES[@]} -gt 0 ]; then
        {
          echo "Critical Service Alert"
          echo "===================="
          echo ""
          echo "Hostname: $HOSTNAME"
          echo "Timestamp: $TIMESTAMP"
          echo ""
          echo "Failed Services:"
          printf '%s\n' "''${FAILED_SERVICES[@]}" | sed 's/^/  - /'
          echo ""
          echo "System Status:"
          systemctl status --all | grep -E "failed|inactive" || true
        } | ${pkgs.bash}/bin/bash -c "{ echo 'From: root@superheavy'; echo 'To: brottman@gmail.com'; echo 'Subject: ALERT: Critical services down on $HOSTNAME'; echo ''; cat; } | ${pkgs.msmtp}/bin/msmtp brottman@gmail.com"
      fi
    '';
    serviceConfig = {
      Type = "oneshot";
      User = "root";
    };
  };

  systemd.timers.critical-service-monitor = {
    description = "Timer for critical service monitoring";
    timerConfig = {
      # Run every 30 minutes
      OnBootSec = "5min";
      OnUnitActiveSec = "30min";
      Persistent = true;
      Unit = "critical-service-monitor.service";
    };
    wantedBy = [ "timers.target" ];
  };

  # Override critical services to notify on failure
  systemd.services.samba.onFailure = [ "service-failure-handler.service" ];
  systemd.services.postfix.onFailure = [ "service-failure-handler.service" ];
  systemd.services.docker.onFailure = [ "service-failure-handler.service" ];
}
