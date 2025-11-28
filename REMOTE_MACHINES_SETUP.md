# Remote Machines Setup Guide

## Quick Start

1. **Create the config file:**
   ```bash
   cp .manage-remote-machines.yaml.example .manage-remote-machines.yaml
   ```

2. **Edit `.manage-remote-machines.yaml`** with your remote machines

3. **Restart the manage script** - remote machines will appear in the machine list

## Configuration Options

Each remote machine requires:
- `name`: A friendly name for the machine (appears in the UI)
- `host`: Hostname or IP address

Optional fields:
- `user`: SSH username (defaults to current user if not specified)
- `port`: SSH port (default: 22)
- `key_file`: Path to SSH private key (e.g., `~/.ssh/id_rsa`)
- `use_agent`: Use SSH agent if available (default: `true`)
- `timeout`: Connection timeout in seconds (default: 10)
- `enabled`: Enable/disable this machine (default: `true`)

## Example Configurations

### Basic Setup (using SSH agent)
```yaml
machines:
  - name: "my-server"
    host: "server.example.com"
    user: "admin"
    enabled: true
```

### Using SSH Key File
```yaml
machines:
  - name: "my-server"
    host: "server.example.com"
    user: "admin"
    key_file: "/home/brian/.ssh/id_rsa"
    use_agent: false
    enabled: true
```

### Custom SSH Port
```yaml
machines:
  - name: "my-server"
    host: "server.example.com"
    user: "admin"
    port: 2222
    enabled: true
```

## Using Remote Machines

1. **Press `m`** in the manage script to open the machine selection screen
2. **Remote machines** will appear with a `(remote)` label in yellow
3. **Connection status** is tested automatically:
   - ✓ Connected - ready to use
   - ✗ Connection failed - check your SSH configuration
4. **Select a remote machine** and run commands - they'll execute via SSH automatically

## Troubleshooting

- **No remote machines showing?** Check that `.manage-remote-machines.yaml` exists and has valid entries
- **Connection failed?** Test SSH manually: `ssh user@host`
- **Key file not found?** Use absolute paths or ensure `~` expands correctly
- **Permission denied?** Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
