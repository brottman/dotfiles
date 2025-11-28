#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.rich python3Packages.textual python3Packages.pyyaml
"""
manage.py - System Management Console v1.02
A beautiful terminal user interface for managing NixOS, Docker, System, Git, Network, Services, and Storage.
"""

import subprocess
import sys
import os
import shutil
import threading
import textwrap
import pty
import fcntl
import time
import json
import re
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Callable, Union
from dataclasses import dataclass

try:
    import yaml
except ImportError:
    yaml = None

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header, Footer, Static, Label, Button, Log, 
        Tab, TabbedContent, TabPane, Input, Select
    )
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
    from textual.binding import Binding
    from textual import on, events
    from textual.message import Message
    from textual.reactive import reactive
    from textual.screen import Screen, ModalScreen
except ImportError:
    print("Error: textual library not found. Please install it with:")
    print("  pip install textual")
    print("  or")
    print("  nix-shell -p python3Packages.textual")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.text import Text
except ImportError:
    print("Error: rich library not found. Please install it with:")
    print("  pip install rich")
    print("  or")
    print("  nix-shell -p python3Packages.rich")
    sys.exit(1)


# =============================================================================
# Version Information
# =============================================================================

VERSION = "1.02"


# =============================================================================
# Configuration Loading
# =============================================================================

def _get_default_tabs() -> List[Tuple[str, str, str]]:
    """Return default tab definitions."""
    return [
        ("system", "System", "🖥️"),
        ("nixos", "NixOS", "❄️"),
        ("docker", "Docker", "🐳"),
        ("git", "Git", "📂"),
        ("network", "Network", "🌐"),
        ("services", "Services", "⚙️"),
        ("storage", "Storage", "💾"),
        ("vm", "Virtual Machines", "💻"),
    ]


def _get_default_actions() -> Dict[str, List[Tuple[str, str, str, bool, bool]]]:
    """Return default action definitions."""
    return {
    "nixos": [
        ("switch", "Switch Configuration", "Apply NixOS configuration immediately using nixos-rebuild switch", False, True),
        ("boot", "Boot Configuration", "Build and set configuration for next boot without activating", False, True),
        ("update-nixpkgs", "Update Nixpkgs", "Update only the nixpkgs input", False, False),
        ("rebuild-all", "Rebuild All Machines", "Build configurations for all defined machines", False, False),
        ("status", "List Generations", "Show current and available NixOS generations", False, True),
        ("gc", "Garbage Collection", "Remove old generations and free up disk space", False, False),
        ("list", "List Machines", "Show all available machine configurations", False, False),
        ("devshells", "Show devShells", "List all available development shells from the flake", False, False),
    ],
    "docker": [
        ("docker-ps", "List Containers", "Show all running Docker containers", False, False),
        ("docker-ps-all", "List All Containers", "Show all containers including stopped ones", False, False),
        ("docker-images", "List Images", "Show all Docker images on the system", False, False),
        ("docker-compose-up", "Compose Up", "Start all services defined in docker-compose.yml", False, False),
        ("docker-compose-down", "Compose Down", "Stop and remove all composed services", False, False),
        ("docker-compose-logs", "Compose Logs", "View logs from all composed services", False, False),
        ("docker-prune-all", "Full Prune", "Remove all unused data including volumes", True, False),
        ("docker-stats", "Container Stats", "Show real-time resource usage of containers", False, False),
        ("docker-networks", "List Networks", "Show all Docker networks", False, False),
        ("docker-volumes", "List Volumes", "Show all Docker volumes", False, False),
        ("docker-restart-all", "Restart All", "Restart all running containers", True, False),
    ],
    "system": [
        ("health", "Health Check", "Run comprehensive system health diagnostics", False, False),
        ("sys-info", "System Info", "Display detailed system information including uptime", False, False),
        ("sys-memory", "Memory Usage", "Display memory and swap usage statistics", False, False),
        ("sys-cpu", "CPU Info", "Show CPU information and current usage", False, False),
        ("sys-processes", "Top Processes", "List processes sorted by resource usage", False, False),
        ("sys-services", "Failed Services", "Show any failed systemd services", False, False),
        ("sys-logs", "System Logs", "View recent system journal logs", False, False),
        ("sys-boot-logs", "Boot Logs", "View logs from the current boot", False, False),
        ("sys-reboot", "Reboot System", "Safely reboot the system", True, False),
        ("sys-shutdown", "Shutdown", "Safely shutdown the system", True, False),
    ],
    "git": [
        ("git-status", "Status", "Show the working tree status", False, False),
        ("git-pull", "Pull", "Fetch and merge changes from remote", False, False),
        ("git-push", "Push", "Push local commits to remote", False, False),
        ("git-log", "Log", "Show recent commit history", False, False),
        ("git-diff", "Diff", "Show uncommitted changes", False, False),
        ("git-branch", "Branches", "List all branches", False, False),
        ("git-stash", "Stash", "Stash current changes", False, False),
        ("git-stash-pop", "Stash Pop", "Apply and remove the latest stash", False, False),
        ("git-fetch", "Fetch", "Download objects from remote", False, False),
        ("git-reset", "Reset Hard", "Reset working directory to HEAD", True, False),
        ("git-clean", "Clean", "Remove untracked files", True, False),
    ],
    "network": [
        ("net-ip", "Network Status", "Display all IP addresses", False, False),
        ("net-connections", "Active Connections", "Show all active network connections", False, False),
        ("net-ports", "Listening Ports", "Show all listening ports", False, False),
        ("net-ping", "Ping Test", "Test connectivity to common endpoints", False, False),
        ("net-dns", "DNS Lookup", "Perform DNS resolution tests", False, False),
        ("net-trace", "Traceroute", "Trace route to a destination", False, False),
        ("net-wifi", "WiFi Status", "Show WiFi connection status", False, False),
        ("net-firewall", "Firewall Rules", "Display current firewall rules", False, False),
        ("net-bandwidth", "Bandwidth Test", "Test network bandwidth (requires speedtest-cli)", False, False),
    ],
    "services": [
        ("svc-list", "List Services", "Show all systemd services", False, False),
        ("svc-running", "Running Services", "Show only running services", False, False),
        ("svc-failed", "Failed Services", "Show failed services", False, False),
        ("svc-timers", "Active Timers", "Show all active systemd timers", False, False),
        ("svc-reload", "Reload Daemon", "Reload systemd daemon configuration", False, False),
        ("svc-nginx", "Nginx Status", "Check nginx web server status", False, False),
        ("svc-postgres", "PostgreSQL Status", "Check PostgreSQL database status", False, False),
        ("svc-redis", "Redis Status", "Check Redis cache status", False, False),
        ("svc-ssh", "SSH Status", "Check SSH server status", False, False),
        ("svc-docker", "Docker Status", "Check Docker daemon status", False, False),
    ],
    "storage": [
        ("disk-usage", "Disk Usage", "Show disk space usage for all mounts", False, False),
        ("disk-free", "Free Space", "Show available disk space", False, False),
        ("disk-mounts", "Mount Points", "List all mounted filesystems", False, False),
        ("disk-io", "I/O Stats", "Show disk I/O statistics", False, False),
        ("disk-largest", "Largest Files", "Find the largest files on disk", False, False),
        ("disk-inodes", "Inode Usage", "Show inode usage for filesystems", False, False),
        ("zfs-status", "ZFS Status", "Show ZFS pool status", False, False),
        ("zfs-list", "ZFS Datasets", "List all ZFS datasets", False, False),
        ("zfs-snapshots", "ZFS Snapshots", "List all ZFS snapshots", False, False),
        ("smart-status", "SMART Status", "Check disk health via SMART", False, False),
    ],
    "vm": [
        ("vm-create", "Create VM", "Create a new virtual machine (interactive wizard)", False, False),
        ("vm-list-all", "List All VMs", "Show all VMs including inactive ones", False, False),
        ("vm-info", "VM Info", "Show detailed information about a VM", False, False),
        ("vm-start", "Start VM", "Start a virtual machine", False, False),
        ("vm-shutdown", "Shutdown VM", "Gracefully shutdown a virtual machine", False, False),
        ("vm-reboot", "Reboot VM", "Reboot a virtual machine", False, False),
        ("vm-force-stop", "Force Stop VM", "Forcefully stop a virtual machine", True, False),
        ("vm-suspend", "Suspend VM", "Suspend a virtual machine to disk", False, False),
        ("vm-resume", "Resume VM", "Resume a suspended virtual machine", False, False),
        ("vm-console", "VM Console", "Open console for a virtual machine", False, False),
        ("vm-stats", "VM Stats", "Show resource usage statistics for VMs", False, False),
        ("vm-networks", "List Networks", "Show all virtual networks", False, False),
        ("vm-pools", "List Storage Pools", "Show all storage pools", False, False),
        ("vm-domains", "List Domains", "Show all libvirt domains", False, False),
    ],
}


def _load_config_from_yaml(config_path: Optional[Path] = None) -> Tuple[
    Optional[List[Tuple[str, str, str]]],
    Optional[Dict[str, List[Tuple[str, str, str, bool, bool]]]]
]:
    """
    Load tabs and actions from YAML configuration file.
    
    Returns:
        Tuple of (tabs, actions) or (None, None) if loading fails.
        tabs: List of (id, name, icon) tuples
        actions: Dict mapping category to list of (id, title, desc, dangerous, requires_machine) tuples
    """
    if yaml is None:
        return None, None
    
    if config_path is None:
        # Look for config file in the same directory as manage.py
        script_dir = Path(__file__).parent.absolute()
        config_path = script_dir / "manage-actions.yaml"
    
    if not config_path.exists():
        return None, None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            return None, None
        
        # Load tabs
        tabs = []
        if 'tabs' in config:
            for tab in config['tabs']:
                tabs.append((
                    tab.get('id', ''),
                    tab.get('name', ''),
                    tab.get('icon', '')
                ))
        
        # Load actions
        actions = {}
        if 'actions' in config:
            for category, action_list in config['actions'].items():
                actions[category] = []
                for action in action_list:
                    actions[category].append((
                        action.get('id', ''),
                        action.get('title', ''),
                        action.get('description', ''),
                        action.get('dangerous', False),
                        action.get('requires_machine', False)
                    ))
        
        return tabs if tabs else None, actions if actions else None
        
    except Exception as e:
        # Silently fall back to defaults on any error
        print(f"Warning: Failed to load config from {config_path}: {e}", file=sys.stderr)
        return None, None


def _get_tabs() -> List[Tuple[str, str, str]]:
    """Get tabs from config file or return defaults."""
    config_path = Path(__file__).parent.absolute() / "manage-actions.yaml"
    tabs, _ = _load_config_from_yaml(config_path)
    return tabs if tabs else _get_default_tabs()


def _get_actions() -> Dict[str, List[Tuple[str, str, str, bool, bool]]]:
    """Get actions from config file or return defaults."""
    config_path = Path(__file__).parent.absolute() / "manage-actions.yaml"
    _, actions = _load_config_from_yaml(config_path)
    return actions if actions else _get_default_actions()


# Load tabs and actions (from config file or defaults)
TABS = _get_tabs()
ACTIONS = _get_actions()

MACHINES = ["brian-laptop", "superheavy", "docker", "backup"]


# =============================================================================
# Command Executor
# =============================================================================

class CommandExecutor:
    """
    Handles command execution, output streaming, and error handling.
    Separates execution logic from UI concerns.
    """
    
    def __init__(self, working_dir: Path, 
                 output_callback: Optional[Callable[[str], None]] = None,
                 spinner_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize CommandExecutor.
        
        Args:
            working_dir: Working directory for command execution
            output_callback: Callback function for output lines (str -> None)
            spinner_callback: Callback function for spinner control ('start'|'stop'|'stop_success')
        """
        self.working_dir = working_dir
        self.output_callback = output_callback or (lambda x: None)
        self.spinner_callback = spinner_callback or (lambda x: None)
    
    def execute(self, cmd: List[str], shell: bool = False, timeout: Optional[int] = None) -> int:
        """
        Execute a command and stream output.
        
        Args:
            cmd: Command to execute as list of strings
            shell: Whether to execute in shell
            timeout: Optional timeout in seconds
            
        Returns:
            Exit code of the command
        """
        try:
            # Log the command being executed
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            self.output_callback(f"Running: {cmd_str}\n\n")
            
            if shell:
                cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                process = subprocess.Popen(
                    cmd_str,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.working_dir,
                    text=True,
                    bufsize=1
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.working_dir,
                    text=True,
                    bufsize=1
                )
            
            # Read output line by line
            output_received = False
            try:
                for line in process.stdout:
                    output_received = True
                    self.output_callback(line)
                
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                self.output_callback(f"\n✗ Command timed out after {timeout} seconds\n")
                self.spinner_callback("stop")
                return 124  # Standard timeout exit code
            
            self.output_callback("\n" + "-" * 60 + "\n")
            
            # Handle success/failure
            if process.returncode == 0:
                self.spinner_callback("stop_success")
                if not output_received:
                    self.output_callback("Command completed (no output)\n")
            else:
                self.spinner_callback("stop")
                self.output_callback(f"✗ Command failed with exit code {process.returncode}\n")
                if not output_received:
                    self.output_callback("No output was produced. The command may have failed silently.\n")
            
            return process.returncode
            
        except FileNotFoundError:
            self.spinner_callback("stop")
            cmd_name = cmd[0] if isinstance(cmd, list) and len(cmd) > 0 else str(cmd)
            self.output_callback(f"✗ Error: Command not found: {cmd_name}\n")
            self.output_callback("Make sure the command is installed and available in PATH.\n")
            return 127  # Standard "command not found" exit code
        except Exception as e:
            self.spinner_callback("stop")
            self.output_callback(f"✗ Error executing command: {e}\n")
            import traceback
            self.output_callback(f"Traceback:\n{traceback.format_exc()}\n")
            return 1
    
    def execute_async(self, cmd: List[str], shell: bool = False, 
                     timeout: Optional[int] = None) -> threading.Thread:
        """
        Execute a command asynchronously in a separate thread.
        
        Args:
            cmd: Command to execute
            shell: Whether to execute in shell
            timeout: Optional timeout in seconds
            
        Returns:
            Thread object (already started)
        """
        def run_in_thread():
            self.execute(cmd, shell=shell, timeout=timeout)
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        return thread
    
    def run_sync(self, cmd: List[str], capture_output: bool = True, 
                timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Run a command synchronously and return the result.
        Useful for commands that need their output captured.
        
        Args:
            cmd: Command to execute
            capture_output: Whether to capture stdout/stderr
            timeout: Optional timeout in seconds
            
        Returns:
            CompletedProcess object
        """
        return subprocess.run(
            cmd,
            cwd=self.working_dir,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )


# =============================================================================
# Command Registry
# =============================================================================

class CommandRegistry:
    """
    Registry for command handlers.
    Allows registering and executing commands by action_id.
    """
    
    def __init__(self) -> None:
        self._commands: Dict[str, Callable[..., None]] = {}
    
    def register(self, action_id: str, handler: Callable[..., None]) -> None:
        """Register a command handler for an action_id."""
        self._commands[action_id] = handler
    
    def execute(self, action_id: str, *args: Any, **kwargs: Any) -> None:
        """
        Execute a command by action_id.
        
        Args:
            action_id: The action identifier
            *args, **kwargs: Arguments to pass to the handler
            
        Raises:
            KeyError: If action_id is not registered
        """
        if action_id not in self._commands:
            raise KeyError(f"Unknown action: {action_id}")
        self._commands[action_id](*args, **kwargs)
    
    def has_command(self, action_id: str) -> bool:
        """Check if an action_id is registered."""
        return action_id in self._commands


# =============================================================================
# Custom Widgets
# =============================================================================

class ActionItem(Static):
    """A clickable action item."""
    
    class Selected(Message):
        """Message sent when action is selected."""
        def __init__(self, action_id: str, category: str) -> None:
            self.action_id = action_id
            self.category = category
            super().__init__()
    
    def __init__(self, action_id: str, title: str, desc: str, dangerous: bool, 
                 category: str, index: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.action_id = action_id
        self.title = title
        self.desc = desc
        self.dangerous = dangerous
        self.category = category
        self.index = index
        self._selected = False
    
    def compose(self) -> ComposeResult:
        danger_badge = " [red]![/red]" if self.dangerous else ""
        yield Label(f"  {self.title}{danger_badge}")
    
    def on_click(self, event: events.Click) -> None:
        self.post_message(ActionItem.Selected(self.action_id, self.category))
    
    def select(self) -> None:
        self._selected = True
        self.add_class("selected")
        label = self.query_one(Label)
        danger_badge = " [red]![/red]" if self.dangerous else ""
        label.update(f"❯ {self.title}{danger_badge}")
    
    def deselect(self) -> None:
        self._selected = False
        self.remove_class("selected")
        label = self.query_one(Label)
        danger_badge = " [red]![/red]" if self.dangerous else ""
        label.update(f"  {self.title}{danger_badge}")


class ActionList(Static, can_focus=True):
    """Widget for displaying and selecting actions in a category."""
    
    class ActionExecute(Message):
        """Message sent when an action should be executed."""
        def __init__(self, action_id: str, title: str, dangerous: bool, requires_machine: bool) -> None:
            self.action_id = action_id
            self.title = title
            self.dangerous = dangerous
            self.requires_machine = requires_machine
            super().__init__()
    
    def __init__(self, category: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.category = category
        self.selected_index = 0
        self.actions = ACTIONS.get(category, [])
    
    def compose(self) -> ComposeResult:
        with ScrollableContainer(id=f"action-scroll-{self.category}"):
            for idx, (action_id, title, desc, dangerous, requires_machine) in enumerate(self.actions):
                yield ActionItem(
                    action_id, title, desc, dangerous, self.category, idx,
                    id=f"action-{self.category}-{idx}",
                    classes="action-item"
                )
    
    def on_mount(self) -> None:
        self._highlight_selected()
    
    def _highlight_selected(self) -> None:
        for idx in range(len(self.actions)):
            try:
                item = self.query_one(f"#action-{self.category}-{idx}", ActionItem)
                if idx == self.selected_index:
                    item.select()
                else:
                    item.deselect()
            except Exception:
                pass
    
    def select_next(self) -> None:
        if len(self.actions) == 0:
            return
        if self.selected_index < len(self.actions) - 1:
            self.selected_index += 1
        else:
            # Wrap around to first item
            self.selected_index = 0
        self._highlight_selected()
        self._scroll_to_selected()
    
    def select_previous(self) -> None:
        if len(self.actions) == 0:
            return
        if self.selected_index > 0:
            self.selected_index -= 1
        else:
            # Wrap around to last item
            self.selected_index = len(self.actions) - 1
        self._highlight_selected()
        self._scroll_to_selected()
    
    def _scroll_to_selected(self) -> None:
        try:
            item = self.query_one(f"#action-{self.category}-{self.selected_index}", ActionItem)
            item.scroll_visible()
        except Exception:
            pass
    
    def get_selected(self) -> Tuple[str, str, bool, bool]:
        if self.actions:
            action_id, title, desc, dangerous, requires_machine = self.actions[self.selected_index]
            return action_id, title, dangerous, requires_machine
        return "", "", False, False
    
    def get_selected_description(self) -> str:
        if self.actions:
            _, title, desc, dangerous, requires_machine = self.actions[self.selected_index]
            result = f"[bold]{title}:[/bold] {desc}"
            if requires_machine:
                result += "\n[yellow]⚠ Requires machine selection[/yellow]"
            if dangerous:
                result += "\n[red]⚠ This is a dangerous operation[/red]"
            return result
        return "Select an action to see its description"
    
    @on(ActionItem.Selected)
    def on_action_selected(self, event: ActionItem.Selected) -> None:
        if event.category == self.category:
            for idx, (action_id, _, _, _, _) in enumerate(self.actions):
                if action_id == event.action_id:
                    self.selected_index = idx
                    self._highlight_selected()
                    # Execute the action
                    action_id, title, dangerous, requires_machine = self.get_selected()
                    self.post_message(ActionList.ActionExecute(action_id, title, dangerous, requires_machine))
                    break


class Spinner(Static):
    """A simple spinner widget for showing command execution."""
    
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._spinning = False
        self._frame_index = 0
    
    def start(self) -> None:
        """Start the spinner animation."""
        self._spinning = True
        self._frame_index = 0
        self._update()
    
    def stop(self) -> None:
        """Stop the spinner animation."""
        self._spinning = False
        self.update("")
    
    def stop_success(self) -> None:
        """Stop the spinner and show a green checkmark."""
        self._spinning = False
        # Use larger checkmark character with bold styling
        self.update("[bold green]✔[/bold green]")
    
    def _update(self) -> None:
        """Update the spinner frame."""
        if self._spinning:
            frame = self.SPINNER_FRAMES[self._frame_index % len(self.SPINNER_FRAMES)]
            # Make spinner bigger with bold styling
            self.update(f"[bold cyan]{frame}[/bold cyan]")
            self._frame_index += 1
            self.set_timer(0.1, self._update)


class OutputLog(Log):
    """Widget for displaying command output."""
    
    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup tags from text."""
        import re
        return re.sub(r'\[/?[^\]]+\]', '', text)
    
    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI escape codes from text."""
        import re
        # Remove ANSI escape sequences (color codes, cursor movements, etc.)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def write_line(self, content: str) -> None:
        """Write a line, stripping markup and ANSI codes."""
        if isinstance(content, str):
            content = self._strip_ansi(content)  # Strip ANSI codes first
            content = self._strip_markup(content)  # Then strip Rich markup
        self.write(content)


# =============================================================================
# VM Creation Wizard
# =============================================================================

class VMCreateWizard(ModalScreen):
    """Interactive wizard for creating virtual machines."""
    
    CSS = """
    VMCreateWizard {
        align: center middle;
    }
    
    #wizard-container {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .wizard-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        border-bottom: solid $primary;
    }
    
    .wizard-question {
        padding: 1;
        text-style: bold;
    }
    
    .wizard-option {
        padding: 0 2;
        margin: 0 1;
    }
    
    .wizard-option.selected {
        background: $primary 40%;
    }
    
    .wizard-input {
        margin: 1;
    }
    
    .wizard-buttons {
        height: 3;
        align: center middle;
        padding: 1;
    }
    
    #btn-next {
        width: 20;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select_option", "Select"),
        Binding("up,k", "navigate_up", "Up"),
        Binding("down,j", "navigate_down", "Down"),
    ]
    
    def __init__(self, flake_path: Path, output_log: OutputLog):
        super().__init__()
        self.flake_path = flake_path
        self.output_log = output_log
        self.current_step = 0
        self.selected_index = 0
        self._custom_input_mode = None
        self.vm_config = {
            "name": "",
            "vm_type": "",
            "os_type": "",
            "memory_gb": 4,
            "cpu_cores": 2,
            "disk_gb": 20,
            "network": "default",
            "create_nixos_config": False,
            "create_instance": True,
        }
        
        # Wizard steps
        self.steps = [
            ("vm_type", "VM Type", ["QEMU/KVM via libvirt (recommended)", "Other (specify)"]),
            ("os_type", "Operating System", ["NixOS", "Other Linux", "Windows", "Multiple"]),
            ("name", "VM Name", None),  # Text input
            ("memory", "Memory (GB)", ["2", "4", "8", "16", "32", "Custom"]),
            ("cpu", "CPU Cores", ["1", "2", "4", "8", "16", "Custom"]),
            ("disk", "Disk Size (GB)", ["10", "20", "50", "100", "200", "Custom"]),
            ("network", "Network Type", ["default (NAT)", "bridge", "macvtap", "None"]),
            ("features", "Features", ["Create VM instance only", "Generate NixOS configs only", "Both"]),
        ]
    
    def compose(self) -> ComposeResult:
        with Container(id="wizard-container"):
            yield Static("Virtual Machine Creation Wizard", classes="wizard-title")
            yield Static("", id="wizard-question")
            yield Static("", id="wizard-options")
            yield Input(placeholder="Enter VM name...", id="wizard-input", classes="wizard-input")
            yield Static("", id="wizard-input-hint")
            with Horizontal(classes="wizard-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Next", id="btn-next", variant="primary")
                yield Button("Back", id="btn-back", variant="default")
    
    def on_mount(self) -> None:
        self._update_step()
        # Ensure the wizard screen can receive keyboard input
        self.can_focus = True
        # Call after refresh to ensure widgets are mounted
        self.call_after_refresh(self._set_initial_focus)
    
    def _set_initial_focus(self) -> None:
        """Set initial focus based on step type."""
        step_id, question, options = self.steps[self.current_step]
        if options is None:
            # Text input step - focus the input
            try:
                input_widget = self.query_one("#wizard-input", Input)
                self.set_focus(input_widget)
            except:
                pass
        else:
            # Selection step - focus the screen itself or Next button
            try:
                # Focus the screen so it can receive keyboard events
                self.focus()
            except:
                pass
    
    def _update_step(self) -> None:
        """Update the wizard display for current step."""
        if self.current_step >= len(self.steps):
            self._finish_wizard()
            return
        
        step_id, question, options = self.steps[self.current_step]
        question_widget = self.query_one("#wizard-question", Static)
        options_widget = self.query_one("#wizard-options", Static)
        input_widget = self.query_one("#wizard-input", Input)
        hint_widget = self.query_one("#wizard-input-hint", Static)
        
        question_widget.update(f"Step {self.current_step + 1}/{len(self.steps)}: {question}")
        
        # Handle text input steps
        if options is None:
            options_widget.update("")
            # For name input, show text input
            if step_id == "name":
                input_widget.visible = True
                input_widget.value = self.vm_config.get("name", "")
                input_widget.placeholder = "Enter VM name (e.g., my-vm)"
                hint_widget.update("Press Enter to confirm, or click Next")
                self.set_focus(input_widget)
            else:
                input_widget.visible = False
                hint_widget.update("")
            return
        
        # Handle selection steps
        input_widget.visible = False
        self._custom_input_mode = None
        hint_widget.update("Use ↑↓ to navigate, Enter to select, or click [bold]Next[/bold] button")
        options_text = ""
        for idx, option in enumerate(options):
            marker = "❯" if idx == self.selected_index else " "
            options_text += f"{marker} {option}\n"
        options_widget.update(options_text)
        # Ensure screen can receive keyboard input for selection steps
        self.call_after_refresh(lambda: self.focus())
        # Also ensure Next button is visible and enabled
        try:
            btn_next = self.query_one("#btn-next", Button)
            btn_next.disabled = False
        except:
            pass
    
    def action_navigate_up(self) -> None:
        if self.current_step >= len(self.steps):
            return
        step_id, question, options = self.steps[self.current_step]
        if options and self.selected_index > 0:
            self.selected_index -= 1
            self._update_step()
        elif options is None:
            # For input steps, focus stays on input
            pass
    
    def action_navigate_down(self) -> None:
        if self.current_step >= len(self.steps):
            return
        step_id, question, options = self.steps[self.current_step]
        if options and self.selected_index < len(options) - 1:
            self.selected_index += 1
            self._update_step()
        elif options is None:
            # For input steps, focus stays on input
            pass
    
    def action_select_option(self) -> None:
        """Handle Enter key - select option or move to next step."""
        if self.current_step >= len(self.steps):
            return
        step_id, question, options = self.steps[self.current_step]
        
        if options is None:
            # Text input step - handled separately
            return
        
        if not options or self.selected_index >= len(options):
            return
        
        # Handle custom options
        selected = options[self.selected_index]
        if "Custom" in selected and step_id in ["memory", "cpu", "disk"]:
            self._handle_custom_input(step_id)
            return
        
        # Store selection
        if step_id == "vm_type":
            if "Other" in selected:
                # For "Other", we'll just note it but still use libvirt
                self.vm_config["vm_type"] = "libvirt"
                self.vm_config["vm_type_other"] = True
            else:
                # Extract the VM type (everything before the first parenthesis)
                vm_type_str = selected.split("(")[0].strip()
                # Handle "QEMU/KVM via libvirt" -> "libvirt"
                if "libvirt" in vm_type_str.lower():
                    self.vm_config["vm_type"] = "libvirt"
                else:
                    self.vm_config["vm_type"] = vm_type_str
        elif step_id == "os_type":
            self.vm_config["os_type"] = selected
        elif step_id == "memory":
            if "Custom" not in selected:
                self.vm_config["memory_gb"] = int(selected)
            else:
                self._handle_custom_input(step_id)
                return
        elif step_id == "cpu":
            if "Custom" not in selected:
                self.vm_config["cpu_cores"] = int(selected)
            else:
                self._handle_custom_input(step_id)
                return
        elif step_id == "disk":
            if "Custom" not in selected:
                self.vm_config["disk_gb"] = int(selected)
            else:
                self._handle_custom_input(step_id)
                return
        elif step_id == "network":
            net_type = selected.split("(")[0].strip().lower()
            if net_type == "none":
                self.vm_config["network"] = None
            else:
                self.vm_config["network"] = net_type
        elif step_id == "features":
            if "instance only" in selected.lower():
                self.vm_config["create_instance"] = True
                self.vm_config["create_nixos_config"] = False
            elif "configs only" in selected.lower():
                self.vm_config["create_instance"] = False
                self.vm_config["create_nixos_config"] = True
            else:  # Both
                self.vm_config["create_instance"] = True
                self.vm_config["create_nixos_config"] = True
        
        self._next_step()
    
    def _handle_custom_input(self, step_id: str) -> None:
        """Handle custom input for memory, CPU, or disk."""
        # Switch to input mode for custom values
        input_widget = self.query_one("#wizard-input", Input)
        hint_widget = self.query_one("#wizard-input-hint", Static)
        options_widget = self.query_one("#wizard-options", Static)
        
        if step_id == "memory":
            input_widget.visible = True
            input_widget.value = str(self.vm_config.get("memory_gb", 4))
            input_widget.placeholder = "Enter memory in GB (e.g., 16)"
            hint_widget.update("Press Enter to confirm")
            options_widget.update("")
            self.set_focus(input_widget)
            # Store that we're in custom input mode
            self._custom_input_mode = "memory"
        elif step_id == "cpu":
            input_widget.visible = True
            input_widget.value = str(self.vm_config.get("cpu_cores", 2))
            input_widget.placeholder = "Enter CPU cores (e.g., 6)"
            hint_widget.update("Press Enter to confirm")
            options_widget.update("")
            self.set_focus(input_widget)
            self._custom_input_mode = "cpu"
        elif step_id == "disk":
            input_widget.visible = True
            input_widget.value = str(self.vm_config.get("disk_gb", 20))
            input_widget.placeholder = "Enter disk size in GB (e.g., 100)"
            hint_widget.update("Press Enter to confirm")
            options_widget.update("")
            self.set_focus(input_widget)
            self._custom_input_mode = "disk"
    
    @on(Input.Submitted, "#wizard-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        step_id, question, options = self.steps[self.current_step]
        
        if step_id == "name":
            name = event.value.strip()
            if name:
                # Validate VM name (no spaces, valid characters)
                if re.match(r'^[a-zA-Z0-9_-]+$', name):
                    self.vm_config["name"] = name
                    self._next_step()
                else:
                    self.query_one("#wizard-input-hint", Static).update("VM name can only contain letters, numbers, hyphens, and underscores")
            else:
                self.query_one("#wizard-input-hint", Static).update("Please enter a valid VM name")
        elif self._custom_input_mode:
            # Handle custom input for memory, CPU, or disk
            try:
                value = int(event.value.strip())
                if value > 0:
                    if self._custom_input_mode == "memory":
                        self.vm_config["memory_gb"] = value
                    elif self._custom_input_mode == "cpu":
                        self.vm_config["cpu_cores"] = value
                    elif self._custom_input_mode == "disk":
                        self.vm_config["disk_gb"] = value
                    self._custom_input_mode = None
                    self._next_step()
                else:
                    self.query_one("#wizard-input-hint", Static).update("Please enter a positive number")
            except ValueError:
                self.query_one("#wizard-input-hint", Static).update("Please enter a valid number")
    
    @on(Button.Pressed, "#btn-next")
    def on_next(self) -> None:
        """Handle Next button press."""
        try:
            step_id, question, options = self.steps[self.current_step]
        except IndexError:
            # Already at the end
            return
        
        if options is None:
            # Text input step
            if step_id == "name":
                input_widget = self.query_one("#wizard-input", Input)
                name = input_widget.value.strip()
                if name:
                    if re.match(r'^[a-zA-Z0-9_-]+$', name):
                        self.vm_config["name"] = name
                        self._next_step()
                    else:
                        self.query_one("#wizard-input-hint", Static).update("VM name can only contain letters, numbers, hyphens, and underscores")
                else:
                    self.query_one("#wizard-input-hint", Static).update("Please enter a valid VM name")
            return
        
        if self._custom_input_mode:
            # In custom input mode, submit the input
            input_widget = self.query_one("#wizard-input", Input)
            try:
                value = int(input_widget.value.strip())
                if value > 0:
                    if self._custom_input_mode == "memory":
                        self.vm_config["memory_gb"] = value
                    elif self._custom_input_mode == "cpu":
                        self.vm_config["cpu_cores"] = value
                    elif self._custom_input_mode == "disk":
                        self.vm_config["disk_gb"] = value
                    self._custom_input_mode = None
                    self._next_step()
                else:
                    self.query_one("#wizard-input-hint", Static).update("Please enter a positive number")
            except ValueError:
                self.query_one("#wizard-input-hint", Static).update("Please enter a valid number")
            return
        
        # For selection steps, use selected option
        if options and len(options) > 0:
            # Make sure we have a valid selection
            if self.selected_index >= len(options):
                self.selected_index = 0
            self.action_select_option()
        else:
            # This shouldn't happen, but if it does, just move to next step
            self._next_step()
    
    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1
            self.selected_index = 0
            self._update_step()
    
    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def _next_step(self) -> None:
        """Move to next step."""
        self.current_step += 1
        self.selected_index = 0
        self._update_step()
    
    def _finish_wizard(self) -> None:
        """Complete the wizard and create the VM."""
        # Validate configuration
        if not self.vm_config.get("name"):
            self.vm_config["name"] = f"vm-{int(time.time())}"
        
        # Update UI to show we're finishing
        try:
            question_widget = self.query_one("#wizard-question", Static)
            options_widget = self.query_one("#wizard-options", Static)
            hint_widget = self.query_one("#wizard-input-hint", Static)
            question_widget.update("Creating VM...")
            options_widget.update("Please wait while the VM is being created.\nThis may take a few moments.")
            hint_widget.update("")
        except:
            pass
        
        # Create VM based on configuration
        self.output_log.write_line("\n" + "=" * 60 + "\n")
        self.output_log.write_line("VM Creation Summary:\n")
        self.output_log.write_line(f"  Name: {self.vm_config['name']}\n")
        self.output_log.write_line(f"  Type: {self.vm_config['vm_type']}\n")
        self.output_log.write_line(f"  OS: {self.vm_config['os_type']}\n")
        self.output_log.write_line(f"  Memory: {self.vm_config['memory_gb']}GB\n")
        self.output_log.write_line(f"  CPU Cores: {self.vm_config['cpu_cores']}\n")
        self.output_log.write_line(f"  Disk: {self.vm_config['disk_gb']}GB\n")
        self.output_log.write_line(f"  Network: {self.vm_config['network']}\n")
        self.output_log.write_line("=" * 60 + "\n\n")
        
        # Create VM
        def create_vm_thread():
            try:
                if self.vm_config["create_nixos_config"] and self.vm_config["os_type"] == "NixOS":
                    self._create_nixos_configs()
                
                if self.vm_config["create_instance"]:
                    self._create_vm_instance()
                
                self.call_from_thread(self.output_log.write_line, "\n✓ VM creation completed!\n")
                self.call_from_thread(self.dismiss, True)
            except Exception as e:
                self.call_from_thread(self.output_log.write_line, f"\n✗ Error creating VM: {e}\n")
                import traceback
                self.call_from_thread(self.output_log.write_line, traceback.format_exc() + "\n")
                self.call_from_thread(self.dismiss, False)
        
        thread = threading.Thread(target=create_vm_thread, daemon=True)
        thread.start()
    
    def _create_nixos_configs(self) -> None:
        """Generate NixOS configuration files for the VM."""
        vm_name = self.vm_config["name"]
        vm_dir = self.flake_path / "machines" / vm_name
        vm_dir.mkdir(parents=True, exist_ok=True)
        
        self.call_from_thread(self.output_log.write_line, f"Generating NixOS configs for {vm_name}...\n")
        
        # Generate configuration.nix
        config_nix = f"""# {vm_name} VM configuration
{{ config, pkgs, ... }}:

{{
  imports = [
    ../../common/common.nix
  ];

  # Allow unfree packages
  nixpkgs.config.allowUnfree = true;

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Networking
  networking.hostName = "{vm_name}";
  networking.networkmanager.enable = true;

  # No GUI by default (can be enabled later)
  services.xserver.enable = false;

  # System packages
  environment.systemPackages = with pkgs; [
    # Add your packages here
  ];
}}
"""
        
        # Generate hardware-configuration.nix
        hardware_nix = f"""# {vm_name} VM hardware configuration
{{ config, lib, pkgs, modulesPath, ... }}:

{{
  imports = [ ];

  # Boot configuration
  boot.initrd.availableKernelModules = [ "sd_mod" "sr_mod" ];
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ];
  boot.extraModulePackages = [ ];
  
  # Bootloader settings
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # File systems - VM will use virtual disk
  # These will be configured when the VM is first booted
  fileSystems."/" = {{
    device = "/dev/disk/by-uuid/CHANGE-ME";
    fsType = "ext4";
  }};

  swapDevices = [ ];

  # Networking
  networking.useDHCP = lib.mkDefault true;

  # Hardware
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}}
"""
        
        # Write files
        (vm_dir / "configuration.nix").write_text(config_nix)
        (vm_dir / "hardware-configuration.nix").write_text(hardware_nix)
        
        self.call_from_thread(self.output_log.write_line, f"✓ Created {vm_dir}/configuration.nix\n")
        self.call_from_thread(self.output_log.write_line, f"✓ Created {vm_dir}/hardware-configuration.nix\n")
        
        # Update flake.nix
        self._update_flake_nix(vm_name)
    
    def _update_flake_nix(self, vm_name: str) -> None:
        """Add VM configuration to flake.nix."""
        flake_path = self.flake_path / "flake.nix"
        flake_content = flake_path.read_text()
        
        # Check if VM already exists in flake
        if f'"{vm_name}"' in flake_content:
            self.call_from_thread(self.output_log.write_line, f"⚠ {vm_name} already exists in flake.nix, skipping update\n")
            return
        
        # Find the nixosConfigurations section
        # Add new configuration before the closing brace
        new_config = f"""
        # {vm_name} VM configuration
        {vm_name} = nixpkgs.lib.nixosSystem {{
          inherit system;
          modules = [
            ./machines/{vm_name}/configuration.nix
            ./machines/{vm_name}/hardware-configuration.nix
          ];
        }};
"""
        
        # Insert before the closing brace of nixosConfigurations
        pattern = r'(nixosConfigurations = \{)(.*?)(\s+\};)'
        match = re.search(pattern, flake_content, re.DOTALL)
        
        if match:
            before = match.group(1) + match.group(2)
            after = match.group(3)
            new_content = before + new_config + after
            flake_path.write_text(new_content)
            self.call_from_thread(self.output_log.write_line, f"✓ Updated flake.nix with {vm_name} configuration\n")
        else:
            self.call_from_thread(self.output_log.write_line, f"⚠ Could not automatically update flake.nix\n")
            self.call_from_thread(self.output_log.write_line, f"Please manually add the {vm_name} configuration\n")
    
    def _create_vm_instance(self) -> None:
        """Create the actual VM instance using virt-install."""
        # Check if virt-install is available
        if not shutil.which("virt-install"):
            self.call_from_thread(self.output_log.write_line, "Error: virt-install command not found.\n")
            self.call_from_thread(self.output_log.write_line, "Please install virt-install:\n")
            self.call_from_thread(self.output_log.write_line, "  nix-shell -p virt-manager\n")
            self.call_from_thread(self.output_log.write_line, "Or via NixOS: programs.virt-manager.enable = true;\n")
            raise Exception("virt-install not found")
        
        vm_name = self.vm_config["name"]
        memory_mb = self.vm_config["memory_gb"] * 1024
        vcpus = self.vm_config["cpu_cores"]
        disk_gb = self.vm_config["disk_gb"]
        network = self.vm_config["network"]
        os_type = self.vm_config["os_type"]
        
        self.call_from_thread(self.output_log.write_line, f"Creating VM instance: {vm_name}...\n")
        
        # Determine OS variant
        os_variant = "generic"
        if os_type == "NixOS":
            os_variant = "nixos"
        elif os_type == "Windows":
            os_variant = "win10"
        elif os_type == "Other Linux":
            os_variant = "generic"
        
        # Build virt-install command
        # Use --import to create VM without installation source (blank disk)
        # We'll create the disk using virt-install's --disk size= option with --import
        cmd = [
            "virt-install",
            "--name", vm_name,
            "--memory", str(memory_mb),
            "--vcpus", str(vcpus),
            "--disk", f"size={disk_gb},format=qcow2",
            "--os-variant", os_variant,
            "--noautoconsole",
            "--import",  # Import mode - creates VM without installation source
        ]
        
        # Add network
        if network is None:
            # No network
            pass
        elif network == "default":
            cmd.extend(["--network", "default"])
        elif network == "bridge":
            # Try to find a bridge
            try:
                result = subprocess.run(
                    ["virsh", "net-list", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    bridge = result.stdout.strip().split("\n")[0]
                    cmd.extend(["--network", f"bridge={bridge}"])
                else:
                    cmd.extend(["--network", "default"])
            except:
                cmd.extend(["--network", "default"])
        elif network == "macvtap":
            cmd.extend(["--network", "type=direct,source=eth0,mode=bridge"])
        
        # For NixOS, add console support
        if os_type == "NixOS":
            cmd.extend(["--graphics", "none", "--console", "pty,target_type=serial"])
        else:
            # Add basic graphics for other OS types
            cmd.extend(["--graphics", "vnc"])
        
        self.call_from_thread(self.output_log.write_line, f"Running: {' '.join(cmd)}\n\n")
        
        # Run virt-install with timeout to prevent hanging
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.flake_path,
                timeout=60  # 60 second timeout
            )
        except subprocess.TimeoutExpired:
            self.call_from_thread(self.output_log.write_line, f"✗ Error: virt-install timed out after 60 seconds\n")
            raise Exception("virt-install timed out")
        
        if result.returncode == 0:
            self.call_from_thread(self.output_log.write_line, f"✓ VM {vm_name} created successfully!\n")
            self.call_from_thread(self.output_log.write_line, f"\nTo start the VM: virsh start {vm_name}\n")
            self.call_from_thread(self.output_log.write_line, f"To view console: virsh console {vm_name}\n")
        else:
            self.call_from_thread(self.output_log.write_line, f"✗ Error creating VM:\n{result.stderr}\n")
            raise Exception(f"virt-install failed: {result.stderr}")


class RelaunchPrompt(ModalScreen):
    """Modal dialog prompting user to relaunch the manage script."""
    
    CSS = """
    RelaunchPrompt {
        align: center middle;
    }
    
    #relaunch-container {
        width: 70;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .relaunch-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        border-bottom: solid $primary;
    }
    
    .relaunch-message {
        padding: 2;
        text-align: center;
    }
    
    .relaunch-buttons {
        height: 3;
        align: center middle;
        padding: 1;
    }
    
    #btn-ok {
        width: 20;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "relaunch", "Relaunch"),
    ]
    
    def compose(self) -> ComposeResult:
        with Container(id="relaunch-container"):
            yield Static("⚠️  Relaunch Required", classes="relaunch-title")
            yield Static(
                "The manage script has been updated.\n\n"
                "Press Enter to relaunch the script automatically.",
                classes="relaunch-message"
            )
            with Horizontal(classes="relaunch-buttons"):
                yield Button("Relaunch", id="btn-ok", variant="primary")
    
    def _relaunch_script(self) -> None:
        """Relaunch the manage script."""
        script_path = Path(__file__).resolve()
        try:
            # Try os.execv first (replaces current process)
            os.execv(script_path, [str(script_path)] + sys.argv[1:])
        except Exception:
            # If execv fails, try subprocess
            try:
                subprocess.run([sys.executable, str(script_path)] + sys.argv[1:])
                sys.exit(0)
            except Exception:
                # If both fail, just dismiss
                self.dismiss(False)
    
    @on(Button.Pressed, "#btn-ok")
    def on_ok(self) -> None:
        self._relaunch_script()
    
    def action_relaunch(self) -> None:
        """Action handler for Enter key - relaunches the script."""
        self._relaunch_script()
    
    def action_cancel(self) -> None:
        """Action handler for Escape key - dismisses without relaunching."""
        self.dismiss(False)


# =============================================================================
# Main Application
# =============================================================================

class ManageApp(App):
    """Main TUI application for manage.py."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        width: 100%;
        height: 100%;
    }
    
    #content-area {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }
    
    #action-panel {
        width: 35;
        min-width: 30;
        border: solid $primary;
        padding: 0 1;
    }
    
    #output-panel {
        width: 1fr;
        border: solid $primary;
        padding: 0 1;
    }
    
    #output-content {
        height: 1fr;
    }
    
    .action-item {
        height: 1;
        padding: 0 1;
    }
    
    .action-item:hover {
        background: $primary 20%;
    }
    
    .action-item.selected {
        background: $primary 40%;
        color: $text;
    }
    
    #description-box {
        height: 5;
        padding: 1;
    }
    
    #status-bar {
        dock: bottom;
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
    }
    
    #tabs-header {
        height: auto;
        layout: horizontal;
        border: solid $primary;
        border-bottom: solid $border;
        padding: 0 1;
    }
    
    TabbedContent {
        width: 1fr;
        height: auto;
    }
    
    Tab {
        border-bottom: none !important;
    }
    
    Tab.--active {
        border-bottom: none !important;
    }
    
    TabList {
        border-bottom: none !important;
    }
    
    TabPane {
        padding: 0;
        height: 0;
    }
    
    #spinner {
        height: auto;
        text-align: right;
        padding: 0 1;
        width: auto;
        text-style: bold;
        content-align: right middle;
    }
    
    #output-log {
        height: 1fr;
        border: none;
    }
    
    #machine-selector {
        dock: top;
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("up,k", "navigate_up", "Up", show=False),
        Binding("down,j", "navigate_down", "Down", show=False),
        Binding("left,h", "prev_tab", "Prev Tab", show=False),
        Binding("right,l", "next_tab", "Next Tab", show=False),
        Binding("enter", "execute_action", "Execute"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
        Binding("1", "tab_1", "System", show=False),
        Binding("2", "tab_2", "NixOS", show=False),
        Binding("3", "tab_3", "Docker", show=False),
        Binding("4", "tab_4", "Git", show=False),
        Binding("5", "tab_5", "Network", show=False),
        Binding("6", "tab_6", "Services", show=False),
        Binding("7", "tab_7", "Storage", show=False),
        Binding("8", "tab_8", "VMs", show=False),
        Binding("m", "cycle_machine", "Machine"),
        Binding("c", "clear_output", "Clear"),
    ]
    
    current_tab = reactive("system")
    
    def __init__(self) -> None:
        super().__init__()
        self.title = f"System Management Console v{VERSION}"
        self.flake_path: Path = Path(__file__).parent.absolute()
        self.machines_list: List[str] = MACHINES
        self.current_machine: Optional[str] = self._detect_current_machine()
        self.machine_index: int = 0
        if self.current_machine in self.machines_list:
            self.machine_index = self.machines_list.index(self.current_machine)
        self._current_process = None
        self._current_process_exit_code = None
        self._pending_dangerous_action = None  # (action_id, title, requires_machine)
        self._dangerous_confirmation_count = 0
        
        # Initialize command registry
        self._command_registry = CommandRegistry()
        
        # Initialize command executor
        self._command_executor = CommandExecutor(
            working_dir=self.flake_path,
            output_callback=self._output_callback,
            spinner_callback=self._spinner_callback
        )
        
        self._register_commands()
    
    def _output_callback(self, line: str) -> None:
        """Callback for command output - thread-safe wrapper."""
        output_log = self.query_one("#output-log", OutputLog)
        self.call_from_thread(output_log.write_line, line)
    
    def _spinner_callback(self, action: str) -> None:
        """Callback for spinner control - thread-safe wrapper."""
        spinner = self.query_one("#spinner", Spinner)
        if action == "start":
            self.call_from_thread(spinner.start)
        elif action == "stop":
            self.call_from_thread(spinner.stop)
        elif action == "stop_success":
            self.call_from_thread(spinner.stop_success)
    
    # =============================================================================
    # Helper Methods for Common Patterns
    # =============================================================================
    
    def _get_spinner(self) -> Spinner:
        """Get the spinner widget."""
        return self.query_one("#spinner", Spinner)
    
    def _get_output_log(self) -> OutputLog:
        """Get the output log widget."""
        return self.query_one("#output-log", OutputLog)
    
    def _write_output(self, text: str, thread_safe: bool = False) -> None:
        """
        Write text to output log.
        
        Args:
            text: Text to write
            thread_safe: If True, use call_from_thread for thread safety
        """
        output_log = self._get_output_log()
        if thread_safe:
            self.call_from_thread(output_log.write_line, text)
        else:
            output_log.write_line(text)
    
    def _write_separator(self, thread_safe: bool = False) -> None:
        """Write a separator line to output log."""
        self._write_output("\n" + "-" * 60 + "\n", thread_safe=thread_safe)
    
    def _handle_error(self, message: str, thread_safe: bool = False) -> None:
        """
        Handle an error: stop spinner and write error message.
        
        Args:
            message: Error message to display
            thread_safe: If True, use call_from_thread for thread safety
        """
        spinner = self._get_spinner()
        if thread_safe:
            self.call_from_thread(spinner.stop)
            self.call_from_thread(self._get_output_log().write_line, message)
        else:
            spinner.stop()
            self._write_output(message)
    
    def _handle_success(self, message: Optional[str] = None, thread_safe: bool = False) -> None:
        """
        Handle success: stop spinner with success indicator and optionally write message.
        
        Args:
            message: Optional success message to display
            thread_safe: If True, use call_from_thread for thread safety
        """
        spinner = self._get_spinner()
        if thread_safe:
            self.call_from_thread(spinner.stop_success)
            if message:
                self.call_from_thread(self._get_output_log().write_line, message)
        else:
            spinner.stop_success()
            if message:
                self._write_output(message)
    
    def _handle_command_error(self, cmd_name: str, error: Exception, 
                              include_traceback: bool = False, thread_safe: bool = False) -> None:
        """
        Handle command execution error with consistent formatting.
        
        Args:
            cmd_name: Name of the command that failed
            error: Exception that occurred
            include_traceback: Whether to include full traceback
            thread_safe: If True, use call_from_thread for thread safety
        """
        error_msg = f"✗ Error executing {cmd_name}: {error}\n"
        if include_traceback:
            import traceback
            error_msg += f"Traceback:\n{traceback.format_exc()}\n"
        self._handle_error(error_msg, thread_safe=thread_safe)
    
    def _handle_command_not_found(self, cmd_name: str, thread_safe: bool = False) -> None:
        """
        Handle command not found error with helpful message.
        
        Args:
            cmd_name: Name of the command that wasn't found
            thread_safe: If True, use call_from_thread for thread safety
        """
        error_msg = f"✗ Error: Command not found: {cmd_name}\n"
        error_msg += "Make sure the command is installed and available in PATH.\n"
        self._handle_error(error_msg, thread_safe=thread_safe)
    
    def _detect_current_machine(self) -> Optional[str]:
        """Detect the current machine from hostname."""
        try:
            # Use timeout to avoid blocking if hostname command hangs
            hostname = subprocess.check_output(
                ["hostname"], 
                text=True, 
                timeout=1,
                stderr=subprocess.DEVNULL
            ).strip()
            if hostname in self.machines_list:
                return hostname
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            # If hostname fails or times out, just use first machine
            pass
        return self.machines_list[0] if self.machines_list else None
    
    def _register_commands(self) -> None:
        """Register all command handlers in the registry."""
        registry = self._command_registry
        
        # NixOS commands
        registry.register("switch", lambda m, log: self._run_streaming(
            ["sudo", "nixos-rebuild", "switch", "--flake", f".#{m}"], log))
        registry.register("boot", lambda m, log: self._run_streaming(
            ["sudo", "nixos-rebuild", "boot", "--flake", f".#{m}"], log))
        registry.register("update-nixpkgs", lambda m, log: self._run_streaming(
            ["nix", "flake", "update", "nixpkgs", "--extra-experimental-features", "nix-command flakes"], log))
        registry.register("rebuild-all", lambda m, log: self._rebuild_all_machines(log))
        registry.register("status", lambda m, log: self._run_streaming(
            ["nixos-rebuild", "list-generations"], log))
        registry.register("gc", lambda m, log: self._run_streaming(
            ["sudo", "nix-collect-garbage", "-d"], log))
        registry.register("list", lambda m, log: self._list_machines(log))
        registry.register("devshells", lambda m, log: self._list_devshells(log))
        
        # Docker commands
        registry.register("docker-ps", lambda m, log: self._run_streaming(["docker", "ps"], log))
        registry.register("docker-ps-all", lambda m, log: self._run_streaming(["docker", "ps", "-a"], log))
        registry.register("docker-images", lambda m, log: self._run_streaming(["docker", "images"], log))
        registry.register("docker-compose-up", lambda m, log: self._run_streaming(
            ["docker", "compose", "up", "-d"], log))
        registry.register("docker-compose-down", lambda m, log: self._run_streaming(
            ["docker", "compose", "down"], log))
        registry.register("docker-compose-logs", lambda m, log: self._run_streaming(
            ["docker", "compose", "logs", "--tail=50"], log))
        registry.register("docker-prune-all", lambda m, log: self._run_streaming(
            ["docker", "system", "prune", "-af", "--volumes"], log))
        registry.register("docker-stats", lambda m, log: self._run_streaming(
            ["docker", "stats", "--no-stream"], log))
        registry.register("docker-networks", lambda m, log: self._run_streaming(
            ["docker", "network", "ls"], log))
        registry.register("docker-volumes", lambda m, log: self._run_streaming(
            ["docker", "volume", "ls"], log))
        registry.register("docker-restart-all", lambda m, log: self._run_streaming(
            ["sh", "-c", "docker restart $(docker ps -q)"], log, shell=False))
        
        # System commands
        registry.register("health", lambda m, log: self._run_health_check(log))
        registry.register("sys-info", lambda m, log: self._run_system_info(log))
        registry.register("sys-memory", lambda m, log: self._run_streaming(["free", "-h"], log))
        registry.register("sys-cpu", lambda m, log: self._run_streaming(["lscpu"], log))
        registry.register("sys-processes", lambda m, log: self._run_streaming(
            ["ps", "aux", "--sort=-%mem"], log))
        registry.register("sys-services", lambda m, log: self._run_streaming(
            ["systemctl", "--failed"], log))
        registry.register("sys-logs", lambda m, log: self._run_streaming(
            ["journalctl", "-n", "50", "--no-pager"], log))
        registry.register("sys-boot-logs", lambda m, log: self._run_streaming(
            ["journalctl", "-b", "-n", "50", "--no-pager"], log))
        registry.register("sys-reboot", lambda m, log: self._run_streaming(
            ["sudo", "systemctl", "reboot"], log))
        registry.register("sys-shutdown", lambda m, log: self._run_streaming(
            ["sudo", "systemctl", "poweroff"], log))
        
        # Git commands
        registry.register("git-status", lambda m, log: self._run_streaming(["git", "status"], log))
        registry.register("git-pull", lambda m, log: self._run_git_pull_with_check(log))
        registry.register("git-push", lambda m, log: self._run_streaming(["git", "push"], log))
        registry.register("git-log", lambda m, log: self._run_streaming(
            ["git", "log", "--oneline", "-20"], log))
        registry.register("git-diff", lambda m, log: self._run_streaming(["git", "diff"], log))
        registry.register("git-branch", lambda m, log: self._run_streaming(
            ["git", "branch", "-a"], log))
        registry.register("git-stash", lambda m, log: self._run_streaming(["git", "stash"], log))
        registry.register("git-stash-pop", lambda m, log: self._run_streaming(
            ["git", "stash", "pop"], log))
        registry.register("git-fetch", lambda m, log: self._run_streaming(
            ["git", "fetch", "--all"], log))
        registry.register("git-reset", lambda m, log: self._run_streaming(
            ["git", "reset", "--hard", "HEAD"], log))
        registry.register("git-clean", lambda m, log: self._run_streaming(["git", "clean", "-fd"], log))
        
        # Network commands
        registry.register("net-ip", lambda m, log: self._run_streaming(["ip", "addr", "show"], log))
        registry.register("net-connections", lambda m, log: self._run_streaming(["ss", "-tuln"], log))
        registry.register("net-ports", lambda m, log: self._run_streaming(["ss", "-tlnp"], log))
        registry.register("net-ping", lambda m, log: self._run_ping_test(log))
        registry.register("net-dns", lambda m, log: self._run_dns_test(log))
        registry.register("net-trace", lambda m, log: self._run_streaming(
            ["traceroute", "-m", "15", "8.8.8.8"], log))
        registry.register("net-wifi", lambda m, log: self._run_streaming(
            ["nmcli", "device", "wifi", "list"], log))
        registry.register("net-firewall", lambda m, log: self._run_streaming(
            ["sudo", "iptables", "-L", "-n"], log))
        registry.register("net-bandwidth", lambda m, log: self._run_bandwidth_test(log))
        
        # Services commands
        registry.register("svc-list", lambda m, log: self._run_streaming(
            ["systemctl", "list-units", "--type=service", "--no-pager"], log))
        registry.register("svc-running", lambda m, log: self._run_streaming(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], log))
        registry.register("svc-failed", lambda m, log: self._run_streaming(
            ["systemctl", "--failed", "--no-pager"], log))
        registry.register("svc-timers", lambda m, log: self._run_streaming(
            ["systemctl", "list-timers", "--no-pager"], log))
        registry.register("svc-reload", lambda m, log: self._run_streaming(
            ["sudo", "systemctl", "daemon-reload"], log))
        registry.register("svc-nginx", lambda m, log: self._run_streaming(
            ["systemctl", "status", "nginx", "--no-pager"], log))
        registry.register("svc-postgres", lambda m, log: self._run_streaming(
            ["systemctl", "status", "postgresql", "--no-pager"], log))
        registry.register("svc-redis", lambda m, log: self._run_streaming(
            ["systemctl", "status", "redis", "--no-pager"], log))
        registry.register("svc-ssh", lambda m, log: self._run_streaming(
            ["systemctl", "status", "sshd", "--no-pager"], log))
        registry.register("svc-docker", lambda m, log: self._run_streaming(
            ["systemctl", "status", "docker", "--no-pager"], log))
        
        # Storage commands
        registry.register("disk-usage", lambda m, log: self._run_streaming(["df", "-h"], log))
        registry.register("disk-free", lambda m, log: self._run_streaming(
            ["df", "-h", "--output=target,avail,pcent"], log))
        registry.register("disk-mounts", lambda m, log: self._run_streaming(["mount"], log))
        registry.register("disk-io", lambda m, log: self._run_streaming(
            ["iostat", "-x", "1", "1"], log))
        registry.register("disk-largest", lambda m, log: self._run_streaming(
            ["sudo", "sh", "-c", "du -ah / --max-depth=3 2>/dev/null | sort -rh | head -20"], 
            log, shell=False))
        registry.register("disk-inodes", lambda m, log: self._run_streaming(["df", "-i"], log))
        registry.register("zfs-status", lambda m, log: self._run_streaming(["zpool", "status"], log))
        registry.register("zfs-list", lambda m, log: self._run_streaming(["zfs", "list"], log))
        registry.register("zfs-snapshots", lambda m, log: self._run_streaming(
            ["zfs", "list", "-t", "snapshot"], log))
        registry.register("smart-status", lambda m, log: self._run_smart_status(log))
        
        # Virtual Machine commands
        registry.register("vm-create", lambda m, log: self._vm_create_helper(log))
        registry.register("vm-list-all", self._vm_list_all_handler)
        registry.register("vm-info", lambda m, log: self._vm_info_helper(log))
        registry.register("vm-start", lambda m, log: self._vm_start_helper(log))
        registry.register("vm-shutdown", lambda m, log: self._vm_shutdown_helper(log))
        registry.register("vm-reboot", lambda m, log: self._vm_reboot_helper(log))
        registry.register("vm-force-stop", lambda m, log: self._vm_force_stop_helper(log))
        registry.register("vm-suspend", lambda m, log: self._vm_suspend_helper(log))
        registry.register("vm-resume", lambda m, log: self._vm_resume_helper(log))
        registry.register("vm-console", lambda m, log: self._vm_console_helper(log))
        registry.register("vm-stats", lambda m, log: self._run_vm_stats(log))
        registry.register("vm-networks", lambda m, log: self._run_streaming(
            ["virsh", "net-list", "--all"], log))
        registry.register("vm-pools", lambda m, log: self._run_streaming(
            ["virsh", "pool-list", "--all"], log))
        registry.register("vm-domains", lambda m, log: self._run_streaming(
            ["virsh", "list", "--all"], log))
    
    def _vm_list_all_handler(self, machine: Optional[str], output_log: OutputLog) -> None:
        """Handler for vm-list-all that checks for virsh availability."""
        if not shutil.which("virsh"):
            output_log.write_line("Error: virsh command not found.\n")
            output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
            self._get_spinner().stop()
        else:
            self._run_vm_list_command(output_log, all_vms=True)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main-container"):
            yield Static(
                f"[bold]Machine:[/bold] [green]{self.current_machine}[/green] | "
                f"[dim]Press 'm' to change[/dim]",
                id="machine-selector"
            )
            
            # Tabs pane above all other panes
            with Horizontal(id="tabs-header"):
                with TabbedContent(id="tabs"):
                    for tab_id, tab_name, tab_icon in TABS:
                        with TabPane(f"{tab_icon} {tab_name}", id=f"tab-{tab_id}"):
                            # Empty pane - tabs are just for selection
                            yield Static("")
                yield Spinner(id="spinner")
            
            # Horizontal layout: actions on left, output on right
            with Horizontal(id="content-area"):
                # Left side: Action panel (changes based on tab selection)
                with Vertical(id="action-panel"):
                    # We'll dynamically update this based on tab selection
                    yield ActionList("system", id="actions-current")
                    
                    yield Static(
                        "Select an action to see its description",
                        id="description-box"
                    )
                
                # Right side: Output panel
                with Vertical(id="output-panel"):
                    # Output content
                    with Vertical(id="output-content"):
                        yield OutputLog(id="output-log", highlight=True)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app starts."""
        self._update_description()
        output_log = self.query_one("#output-log", OutputLog)
        output_log.write_line("Ready. Select an action and press Enter to execute.\n")
        # Set focus on the action list so arrow keys work immediately
        # Use call_after_refresh to ensure the widget is fully mounted
        self.call_after_refresh(self._set_initial_focus)
    
    def _set_initial_focus(self) -> None:
        """Set focus on the action list after app is fully mounted."""
        try:
            action_list = self.query_one("#actions-current", ActionList)
            self.set_focus(action_list)
        except Exception:
            pass
    
    def _get_current_action_list(self) -> Optional[ActionList]:
        """Get the ActionList for the current tab."""
        try:
            return self.query_one("#actions-current", ActionList)
        except Exception:
            return None
    
    def _update_description(self) -> None:
        """Update the description box."""
        action_list = self._get_current_action_list()
        if action_list:
            desc = action_list.get_selected_description()
            self.query_one("#description-box", Static).update(desc)
    
    def _update_machine_display(self) -> None:
        """Update the machine selector display."""
        self.query_one("#machine-selector", Static).update(
            f"[bold]Machine:[/bold] [green]{self.current_machine}[/green] | "
            f"[dim]Press 'm' to change[/dim]"
        )
    
    @on(TabbedContent.TabActivated)
    def on_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab change."""
        tab_id = event.pane.id.replace("tab-", "")
        self.current_tab = tab_id
        # Reset dangerous action confirmation when changing tabs
        self._pending_dangerous_action = None
        self._dangerous_confirmation_count = 0
        
        # Update the action list to show actions for the new tab
        action_panel = self.query_one("#action-panel", Vertical)
        
        # Remove existing action list if it exists
        existing_lists = action_panel.query(ActionList)
        for action_list in existing_lists:
            if action_list.id == "actions-current":
                action_list.remove()
        
        # Mount new list after a brief delay to ensure old one is removed
        def mount_new_list():
            # Verify old one is gone
            try:
                action_panel.query_one("#actions-current", ActionList)
                # Still exists, wait a bit more
                self.set_timer(0.05, mount_new_list)
            except Exception:
                # Old one is gone, safe to mount new one
                new_action_list = ActionList(tab_id, id="actions-current")
                action_panel.mount(new_action_list)
                # Set focus on the new action list after it's fully mounted
                self.call_after_refresh(lambda: self.set_focus(new_action_list))
                self._update_description()
        
        self.call_after_refresh(mount_new_list)
    
    def action_navigate_up(self) -> None:
        action_list = self._get_current_action_list()
        if action_list:
            action_list.select_previous()
            self._update_description()
            # Reset dangerous action confirmation when navigating
            self._pending_dangerous_action = None
            self._dangerous_confirmation_count = 0
    
    def action_navigate_down(self) -> None:
        action_list = self._get_current_action_list()
        if action_list:
            action_list.select_next()
            self._update_description()
            # Reset dangerous action confirmation when navigating
            self._pending_dangerous_action = None
            self._dangerous_confirmation_count = 0
    
    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        current_index = self._get_current_tab_index()
        if current_index is not None and current_index < len(TABS) - 1:
            self._switch_to_tab(current_index + 1)
        elif current_index == len(TABS) - 1:
            # Wrap around to first tab
            self._switch_to_tab(0)
    
    def action_prev_tab(self) -> None:
        """Switch to the previous tab."""
        current_index = self._get_current_tab_index()
        if current_index is not None and current_index > 0:
            self._switch_to_tab(current_index - 1)
        elif current_index == 0:
            # Wrap around to last tab
            self._switch_to_tab(len(TABS) - 1)
    
    def _get_current_tab_index(self) -> Optional[int]:
        """Get the index of the currently active tab."""
        try:
            for idx, (tab_id, _, _) in enumerate(TABS):
                if tab_id == self.current_tab:
                    return idx
        except Exception:
            pass
        return 0  # Default to first tab
    
    def action_tab_1(self) -> None:
        self._switch_to_tab(0)
    
    def action_tab_2(self) -> None:
        self._switch_to_tab(1)
    
    def action_tab_3(self) -> None:
        self._switch_to_tab(2)
    
    def action_tab_4(self) -> None:
        self._switch_to_tab(3)
    
    def action_tab_5(self) -> None:
        self._switch_to_tab(4)
    
    def action_tab_6(self) -> None:
        self._switch_to_tab(5)
    
    def action_tab_7(self) -> None:
        self._switch_to_tab(6)
    
    def action_tab_8(self) -> None:
        self._switch_to_tab(7)
    
    def _switch_to_tab(self, index: int) -> None:
        if 0 <= index < len(TABS):
            tab_id = TABS[index][0]
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = f"tab-{tab_id}"
            self.current_tab = tab_id
            self._update_description()
    
    def action_cycle_machine(self) -> None:
        self.machine_index = (self.machine_index + 1) % len(self.machines_list)
        self.current_machine = self.machines_list[self.machine_index]
        self._update_machine_display()
    
    def action_clear_output(self) -> None:
        output_log = self._get_output_log()
        output_log.clear()
        output_log.write_line("Output cleared.\n")
    
    def action_execute_action(self) -> None:
        action_list = self._get_current_action_list()
        if action_list:
            action_id, title, dangerous, requires_machine = action_list.get_selected()
            self._execute_action(action_id, title, dangerous, requires_machine)
    
    @on(ActionList.ActionExecute)
    def on_action_execute(self, event: ActionList.ActionExecute) -> None:
        self._execute_action(event.action_id, event.title, event.dangerous, event.requires_machine)
    
    def _execute_action(self, action_id: str, title: str, dangerous: bool, requires_machine: bool) -> None:
        """Execute an action."""
        output_log = self._get_output_log()
        spinner = self._get_spinner()
        
        # Confirmation for dangerous actions
        if dangerous:
            # Check if we're already in confirmation mode for this action
            if self._pending_dangerous_action is not None:
                pending_id, pending_title, pending_requires_machine = self._pending_dangerous_action
                if pending_id == action_id:
                    # Second Enter press - confirm and execute
                    self._dangerous_confirmation_count = 0
                    self._pending_dangerous_action = None
                    spinner.start()
                    output_log.clear()
                    output_log.write_line(f"Executing: {title}\n")
                    
                    machine = self.current_machine if requires_machine else None
                    if requires_machine:
                        output_log.write_line(f"Machine: {machine}\n")
                    
                    self._write_separator()
                    
                    # Execute the appropriate command
                    self._run_action(action_id, machine, output_log)
                    return
                else:
                    # Different dangerous action selected - reset
                    self._pending_dangerous_action = None
                    self._dangerous_confirmation_count = 0
            
            # First Enter press - show warning and ask for confirmation
            spinner.stop()
            output_log.clear()
            output_log.write_line(f"⚠️  WARNING: '{title}' is a dangerous operation!\n")
            output_log.write_line("Press Enter twice to confirm and execute this command.\n")
            if requires_machine:
                output_log.write_line(f"  Machine: {self.current_machine}\n")
            
            # Store pending action for confirmation
            self._pending_dangerous_action = (action_id, title, requires_machine)
            self._dangerous_confirmation_count = 1
            return
        
        # Reset dangerous action state if a non-dangerous action is selected
        self._pending_dangerous_action = None
        self._dangerous_confirmation_count = 0
        
        spinner.start()
        output_log.clear()
        output_log.write_line(f"Executing: {title}\n")
        
        machine = self.current_machine if requires_machine else None
        if requires_machine:
            output_log.write_line(f"Machine: {machine}\n")
        
        output_log.write_line("-" * 60 + "\n")
        
        # Execute the appropriate command
        self._run_action(action_id, machine, output_log)
    
    def _run_action(self, action_id: str, machine: Optional[str], output_log: OutputLog) -> None:
        """Run the actual command for an action using the command registry."""
        try:
            self._command_registry.execute(action_id, machine, output_log)
        except KeyError:
            self._handle_error(f"Unknown action: {action_id}\n")
        except Exception as e:
            self._handle_command_error(f"action '{action_id}'", e)
    
    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get SHA256 hash of a file, or None if file doesn't exist."""
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
    
    def _run_git_pull_with_check(self, output_log: OutputLog) -> None:
        """Run git pull and check if manage scripts changed, prompting for relaunch if so."""
        def run_in_thread():
            try:
                # Get file hashes before git pull
                manage_py_path = self.flake_path / "manage.py"
                manage_wrapper_path = self.flake_path / "manage-wrapper.sh"
                
                hash_before_py = self._get_file_hash(manage_py_path)
                hash_before_wrapper = self._get_file_hash(manage_wrapper_path)
                
                # Run git pull
                self.call_from_thread(output_log.write_line, "Running: git pull\n\n")
                
                process = subprocess.Popen(
                    ["git", "pull"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self.flake_path,
                    text=True,
                    bufsize=1
                )
                
                # Read output line by line
                output_received = False
                for line in process.stdout:
                    output_received = True
                    self.call_from_thread(output_log.write_line, line)
                
                process.wait()
                
                self.call_from_thread(output_log.write_line, "\n" + "-" * 60 + "\n")
                
                # Check if manage scripts changed (before stopping spinner)
                hash_after_py = self._get_file_hash(manage_py_path)
                hash_after_wrapper = self._get_file_hash(manage_wrapper_path)
                
                script_changed = (
                    (hash_before_py is not None and hash_after_py is not None and hash_before_py != hash_after_py) or
                    (hash_before_wrapper is not None and hash_after_wrapper is not None and hash_before_wrapper != hash_after_wrapper)
                )
                
                # Stop spinner and show success/failure indicator
                def update_ui():
                    spinner = self.query_one("#spinner", Spinner)
                    if process.returncode == 0:
                        spinner.stop_success()
                        if not output_received:
                            output_log.write_line("Command completed (no output)\n")
                        
                        if script_changed:
                            # Show prompt to relaunch
                            self._show_relaunch_prompt()
                    else:
                        spinner.stop()
                        output_log.write_line(f"✗ Command failed with exit code {process.returncode}\n")
                        if not output_received:
                            output_log.write_line("No output was produced. The command may have failed silently.\n")
                
                self.call_from_thread(update_ui)
                
            except FileNotFoundError:
                def handle_error():
                    self._handle_command_not_found("git", thread_safe=False)
                self.call_from_thread(handle_error)
            except Exception as e:
                def handle_exception():
                    self._handle_command_error("git pull", e, include_traceback=True, thread_safe=False)
                self.call_from_thread(handle_exception)
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _show_relaunch_prompt(self) -> None:
        """Show the relaunch prompt modal."""
        self.push_screen(RelaunchPrompt())
    
    def _run_streaming(self, cmd: List[str], output_log: OutputLog, shell: bool = False) -> None:
        """Run a command and stream output to the log using CommandExecutor."""
        # Start spinner
        self._get_spinner().start()
        
        # Execute command asynchronously
        self._command_executor.execute_async(cmd, shell=shell)
    
    def _rebuild_all_machines(self, output_log: OutputLog) -> None:
        """Rebuild all machine configurations."""
        def run_in_thread():
            # Try to update lock file first if it's out of date
            # This handles the case where flake.nix has new inputs not in lock file
            self.call_from_thread(output_log.write_line, "Updating lock file if needed...\n")
            lock_file_updated = False
            update_result = subprocess.run(
                ["nix", "flake", "update",
                 "--extra-experimental-features", "nix-command flakes"],
                cwd=self.flake_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            if update_result.returncode == 0:
                # Check for GitHub API rate limit warnings (non-critical)
                has_rate_limit_warnings = "API rate limit exceeded" in update_result.stderr
                if has_rate_limit_warnings:
                    self.call_from_thread(output_log.write_line, "⚠ GitHub API rate limit hit (using cached versions)\n")
                    self.call_from_thread(output_log.write_line, "   This is not critical - Nix is using cached data\n")
                    self.call_from_thread(output_log.write_line, "   For higher limits, set GITHUB_TOKEN environment variable\n")
                
                if update_result.stdout.strip() or "Added input" in update_result.stderr:
                    self.call_from_thread(output_log.write_line, "✓ Lock file updated\n\n")
                    lock_file_updated = True
                else:
                    self.call_from_thread(output_log.write_line, "✓ Lock file is up to date\n\n")
            else:
                # If update fails due to permissions, try with sudo
                if "Permission denied" in update_result.stderr:
                    self.call_from_thread(output_log.write_line, "⚠ Permission denied. Trying with sudo...\n")
                    sudo_update_result = subprocess.run(
                        ["sudo", "nix", "flake", "update",
                         "--extra-experimental-features", "nix-command flakes"],
                        cwd=self.flake_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if sudo_update_result.returncode == 0:
                        # Check for GitHub API rate limit warnings (non-critical)
                        has_rate_limit_warnings = "API rate limit exceeded" in sudo_update_result.stderr
                        if has_rate_limit_warnings:
                            self.call_from_thread(output_log.write_line, "⚠ GitHub API rate limit hit (using cached versions)\n")
                            self.call_from_thread(output_log.write_line, "   This is not critical - Nix is using cached data\n")
                        
                        if sudo_update_result.stdout.strip() or "Added input" in sudo_update_result.stderr:
                            self.call_from_thread(output_log.write_line, "✓ Lock file updated (with sudo)\n")
                            lock_file_updated = True
                            # Fix ownership so subsequent operations work without sudo
                            self.call_from_thread(output_log.write_line, "Fixing lock file ownership...\n")
                            import os
                            user = os.getenv("USER") or os.getenv("LOGNAME") or "brian"
                            chown_result = subprocess.run(
                                ["sudo", "chown", f"{user}:{user}", "flake.lock"],
                                cwd=self.flake_path,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if chown_result.returncode == 0:
                                self.call_from_thread(output_log.write_line, "✓ Lock file ownership fixed\n\n")
                            else:
                                self.call_from_thread(output_log.write_line, "⚠ Could not fix ownership (non-critical)\n\n")
                        else:
                            self.call_from_thread(output_log.write_line, "✓ Lock file is up to date\n\n")
                    else:
                        self.call_from_thread(output_log.write_line, f"✗ Failed to update lock file even with sudo:\n{sudo_update_result.stderr[:300]}\n")
                        self.call_from_thread(output_log.write_line, "\nTo fix permissions, run:\n")
                        self.call_from_thread(output_log.write_line, "  sudo chown $USER:$USER flake.lock\n")
                        self.call_from_thread(output_log.write_line, "Then run 'nix flake update' manually.\n\n")
                else:
                    self.call_from_thread(output_log.write_line, f"⚠ Lock file update warning: {update_result.stderr[:200]}\n")
                    self.call_from_thread(output_log.write_line, "   Continuing with builds...\n\n")
            
            # Now build all machines
            # If lock file was just updated, allow it to be updated during builds if needed
            # (in case the update didn't fully complete or there are nested dependencies)
            no_update_flag = [] if lock_file_updated else ["--no-update-lock-file"]
            
            for machine in self.machines_list:
                self.call_from_thread(output_log.write_line, f"\nBuilding {machine}...\n")
                try:
                    cmd = ["nix", "build", f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                           "--extra-experimental-features", "nix-command flakes"] + no_update_flag
                    result = subprocess.run(
                        cmd,
                        cwd=self.flake_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout per build
                    )
                    if result.returncode == 0:
                        self.call_from_thread(output_log.write_line, f"✓ {machine} built successfully\n")
                    else:
                        error_msg = result.stderr
                        # Check for various lock file error messages
                        if ("requires lock file changes" in error_msg or 
                            "Lock file is out of date" in error_msg or
                            "lock file changes but they're not allowed" in error_msg):
                            self.call_from_thread(output_log.write_line, f"✗ {machine} failed: Lock file still needs updates\n")
                            # Try one more update attempt
                            self.call_from_thread(output_log.write_line, "   Attempting to update lock file again...\n")
                            retry_update = subprocess.run(
                                ["sudo", "nix", "flake", "update",
                                 "--extra-experimental-features", "nix-command flakes"],
                                cwd=self.flake_path,
                                capture_output=True,
                                text=True,
                                timeout=120
                            )
                            if retry_update.returncode == 0:
                                self.call_from_thread(output_log.write_line, "   ✓ Lock file updated, retrying build...\n")
                                # Retry the build (allow lock file updates after retry update)
                                retry_cmd = ["nix", "build", f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                                            "--extra-experimental-features", "nix-command flakes"]
                                retry_result = subprocess.run(
                                    retry_cmd,
                                    cwd=self.flake_path,
                                    capture_output=True,
                                    text=True,
                                    timeout=300
                                )
                                if retry_result.returncode == 0:
                                    self.call_from_thread(output_log.write_line, f"✓ {machine} built successfully (after retry)\n")
                                else:
                                    self.call_from_thread(output_log.write_line, f"✗ {machine} still failed after lock file update:\n{retry_result.stderr[:500]}\n")
                            else:
                                self.call_from_thread(output_log.write_line, f"   ✗ Could not update lock file: {retry_update.stderr[:200]}\n")
                                self.call_from_thread(output_log.write_line, "   Please run 'sudo nix flake update' manually\n")
                        else:
                            self.call_from_thread(output_log.write_line, f"✗ {machine} failed:\n{error_msg[:500]}\n")
                except subprocess.TimeoutExpired:
                    self.call_from_thread(output_log.write_line, f"✗ {machine} timed out after 5 minutes\n")
                except Exception as e:
                    self.call_from_thread(output_log.write_line, f"✗ {machine} error: {e}\n")
            
            self.call_from_thread(output_log.write_line, "\n" + "-" * 60 + "\n")
            self.call_from_thread(output_log.write_line, "All machines processed.\n")
            spinner = self.query_one("#spinner", Spinner)
            self.call_from_thread(spinner.stop)
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _list_machines(self, output_log: OutputLog) -> None:
        """List all available machines."""
        output_log.write_line("Available Machines:\n\n")
        for machine in self.machines_list:
            status = "(Current)" if machine == self.current_machine else "(Available)"
            output_log.write_line(f"  💻 {machine} {status}\n")
        self._write_separator()
        self._handle_success()
    
    def _list_devshells(self, output_log: OutputLog) -> None:
        """List all available development shells from the flake."""
        def run_in_thread():
            try:
                # Get flake output as JSON
                result = subprocess.run(
                    ["nix", "flake", "show", "--json"],
                    cwd=str(self.flake_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    self.call_from_thread(output_log.write_line, f"Error running nix flake show:\n{result.stderr}\n")
                    self.call_from_thread(self._get_spinner().stop)
                    return
                
                # Parse JSON output
                try:
                    flake_data = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    self.call_from_thread(output_log.write_line, f"Error parsing flake output: {e}\n")
                    self.call_from_thread(self._get_spinner().stop)
                    return
                
                # Extract devShells
                devshells = flake_data.get("devShells", {})
                
                if not devshells:
                    self.call_from_thread(output_log.write_line, "No devShells found in this flake.\n")
                    self.call_from_thread(self._get_spinner().stop_success)
                    return
                
                self.call_from_thread(output_log.write_line, "Available Development Shells:\n\n")
                
                # Iterate through systems (usually x86_64-linux, etc.)
                for system, shells in devshells.items():
                    self.call_from_thread(output_log.write_line, f"System: {system}\n")
                    for shell_name, shell_info in shells.items():
                        description = shell_info.get("description", "")
                        if description:
                            self.call_from_thread(output_log.write_line, f"  🐚 {shell_name}\n")
                            self.call_from_thread(output_log.write_line, f"      {description}\n")
                        else:
                            self.call_from_thread(output_log.write_line, f"  🐚 {shell_name}\n")
                        self.call_from_thread(output_log.write_line, f"      Enter with: nix develop .#{shell_name}\n")
                
                self.call_from_thread(lambda: self._write_separator())
                self.call_from_thread(self._get_spinner().stop_success)
                
            except subprocess.TimeoutExpired:
                self.call_from_thread(output_log.write_line, "Error: Command timed out\n")
                self.call_from_thread(self._get_spinner().stop)
            except Exception as e:
                self.call_from_thread(output_log.write_line, f"Error listing devShells: {e}\n")
                self.call_from_thread(self._get_spinner().stop)
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _run_health_check(self, output_log: OutputLog) -> None:
        """Run system health check."""
        health_script = self.flake_path / "scripts" / "check-system-health.sh"
        
        if health_script.exists():
            self._run_streaming([str(health_script)], output_log)
        else:
            output_log.write_line("Running basic health checks...\n\n")
            
            # Check Nix daemon
            result = subprocess.run(["systemctl", "is-active", "nix-daemon"], capture_output=True, text=True)
            if result.returncode == 0:
                output_log.write_line("✓ Nix daemon is running\n")
            else:
                output_log.write_line("✗ Nix daemon is not running\n")
            
            # Check disk space
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
            output_log.write_line("\nDisk Space:\n")
            output_log.write_line(result.stdout)
            
            # Check memory
            result = subprocess.run(["free", "-h"], capture_output=True, text=True)
            output_log.write_line("\nMemory:\n")
            output_log.write_line(result.stdout)
            
            self._write_separator()
            self._handle_success()
    
    def _run_system_info(self, output_log: OutputLog) -> None:
        """Display system information."""
        output_log.write_line("System Information:\n\n")
        
        # Hostname
        try:
            hostname = subprocess.check_output(["hostname"], text=True).strip()
            output_log.write_line(f"  Hostname: {hostname}\n")
        except:
            pass
        
        # OS
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_name = line.split("=")[1].strip().strip('"')
                            output_log.write_line(f"  OS: {os_name}\n")
                            break
        except:
            pass
        
        # Kernel
        try:
            kernel = subprocess.check_output(["uname", "-r"], text=True).strip()
            output_log.write_line(f"  Kernel: {kernel}\n")
        except:
            pass
        
        # Architecture
        try:
            arch = subprocess.check_output(["uname", "-m"], text=True).strip()
            output_log.write_line(f"  Arch: {arch}\n")
        except:
            pass
        
        # Uptime
        try:
            # Try pretty format first (GNU/Linux), fallback to standard format
            try:
                uptime = subprocess.check_output(["uptime", "-p"], text=True, stderr=subprocess.DEVNULL).strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to standard uptime format
                uptime = subprocess.check_output(["uptime"], text=True).strip()
            output_log.write_line(f"  Uptime: {uptime}\n")
        except:
            pass
        
        output_log.write_line("\n" + "-" * 60 + "\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop_success()
    
    def _run_ping_test(self, output_log: OutputLog) -> None:
        """Run ping tests to common endpoints."""
        endpoints = [
            ("google.com", "Google"),
            ("cloudflare.com", "Cloudflare"),
            ("github.com", "GitHub"),
        ]
        
        output_log.write_line("Ping Test Results:\n\n")
        
        for host, name in endpoints:
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", host],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Extract time from ping output
                    for line in result.stdout.split("\n"):
                        if "time=" in line:
                            time_ms = line.split("time=")[1].split()[0]
                            output_log.write_line(f"  ✓ {name} ({host}): {time_ms}\n")
                            break
                else:
                    output_log.write_line(f"  ✗ {name} ({host}): unreachable\n")
            except Exception as e:
                output_log.write_line(f"  ✗ {name} ({host}): error\n")
        
        output_log.write_line("\n" + "-" * 60 + "\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop_success()
    
    def _run_dns_test(self, output_log: OutputLog) -> None:
        """Run DNS resolution tests."""
        domains = ["google.com", "github.com", "nixos.org"]
        
        output_log.write_line("DNS Resolution Test:\n\n")
        
        for domain in domains:
            try:
                result = subprocess.run(
                    ["nslookup", domain],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    output_log.write_line(f"  ✓ {domain}: resolved\n")
                else:
                    output_log.write_line(f"  ✗ {domain}: failed\n")
            except subprocess.TimeoutExpired:
                output_log.write_line(f"  ✗ {domain}: timeout\n")
            except Exception:
                output_log.write_line(f"  ✗ {domain}: error\n")
        
        output_log.write_line("\n" + "-" * 60 + "\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop_success()
    
    def _run_bandwidth_test(self, output_log: OutputLog) -> None:
        """Run bandwidth test using speedtest-cli."""
        # Check if speedtest-cli is available
        if not shutil.which("speedtest-cli"):
            output_log.write_line("Error: speedtest-cli is not installed.\n\n")
            output_log.write_line("To install speedtest-cli:\n")
            output_log.write_line("  On NixOS: Add to configuration.nix:\n")
            output_log.write_line("    environment.systemPackages = with pkgs; [ speedtest-cli ];\n\n")
            output_log.write_line("  Or use nix-shell:\n")
            output_log.write_line("    nix-shell -p speedtest-cli\n\n")
            output_log.write_line("  Or install via pip:\n")
            output_log.write_line("    pip install speedtest-cli\n\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
            return
        
        # Run the speedtest
        self._run_streaming(["speedtest-cli"], output_log)
    
    def _run_smart_status(self, output_log: OutputLog) -> None:
        """Check SMART status of drives."""
        output_log.write_line("SMART Status Check:\n\n")
        
        # Find block devices
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,TYPE"],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "disk":
                        device = f"/dev/{parts[0]}"
                        try:
                            smart_result = subprocess.run(
                                ["sudo", "smartctl", "-H", device],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if "PASSED" in smart_result.stdout:
                                output_log.write_line(f"  ✓ {device}: PASSED\n")
                            elif "FAILED" in smart_result.stdout:
                                output_log.write_line(f"  ✗ {device}: FAILED\n")
                            else:
                                output_log.write_line(f"  ? {device}: Unknown\n")
                        except subprocess.TimeoutExpired:
                            output_log.write_line(f"  ? {device}: Timeout\n")
                        except Exception:
                            output_log.write_line(f"  ? {device}: Error checking\n")
        except Exception as e:
            output_log.write_line(f"Error: {e}\n")
        
        output_log.write_line("\n" + "-" * 60 + "\n")
    
    def _get_vm_list(self, all_vms: bool = False) -> List[str]:
        """Get list of VMs. Returns empty list if virsh is not available.
        Tries system session first, then falls back to user session."""
        if not shutil.which("virsh"):
            return []
        
        # Try system session first (qemu:///system)
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                cmd = ["virsh", "-c", uri, "list", "--name"]
                if all_vms:
                    cmd.append("--all")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    vms = [vm.strip() for vm in result.stdout.strip().split("\n") if vm.strip()]
                    if vms:
                        return vms
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        return []
    
    def _get_running_vms(self) -> List[str]:
        """Get list of running VMs. Tries system session first, then falls back to user session."""
        if not shutil.which("virsh"):
            return []
        
        # Try system session first (qemu:///system)
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    vms = [vm.strip() for vm in result.stdout.strip().split("\n") if vm.strip()]
                    if vms:
                        return vms
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        return []
    
    def _run_vm_list_command(self, output_log: OutputLog, all_vms: bool = False) -> None:
        """Run virsh list command. For --all, shows VMs from both system and session with session column."""
        found_any = False
        
        # For "List All VMs", combine VMs from both sessions with session info
        if all_vms:
            all_vm_data = []
            
            # Collect VMs from both sessions
            for uri_name, uri in [("System", "qemu:///system"), ("Session", "qemu:///session")]:
                try:
                    cmd = ["virsh", "-c", uri, "list", "--all"]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split("\n")
                        # Skip header lines (first 2 lines are header and separator)
                        for line in lines[2:]:
                            line = line.strip()
                            if line:
                                # Parse the line: typically "Id   Name              State"
                                # Split by whitespace, but preserve state which may have spaces
                                parts = line.split()
                                if len(parts) >= 3:
                                    vm_id = parts[0]
                                    vm_name = parts[1]
                                    # State might be multiple words like "shut off"
                                    vm_state = " ".join(parts[2:])
                                    all_vm_data.append((vm_id, vm_name, vm_state, uri_name))
                        found_any = True
                except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                    # Silently continue to next session
                    continue
            
            if found_any:
                # Write header with Session column
                output_log.write_line(f"{'Id':<6} {'Name':<30} {'State':<20} {'Session':<10}\n")
                output_log.write_line("-" * 70 + "\n")
                # Write all VM lines
                for vm_id, vm_name, vm_state, session in all_vm_data:
                    output_log.write_line(f"{vm_id:<6} {vm_name:<30} {vm_state:<20} {session:<10}\n")
            else:
                output_log.write_line("No VMs found in system or session.\n")
                output_log.write_line("Make sure libvirtd is running: sudo systemctl start libvirtd\n")
        else:
            # For regular "List VMs", try system first, then session
            for uri in ["qemu:///system", "qemu:///session"]:
                try:
                    cmd = ["virsh", "-c", uri, "list"]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        output_log.write_line(result.stdout)
                        if result.stderr:
                            output_log.write_line(result.stderr)
                        found_any = True
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                    continue
            
            if not found_any:
                output_log.write_line("Error: Could not connect to libvirt.\n")
                output_log.write_line("Make sure libvirtd is running: sudo systemctl start libvirtd\n")
                output_log.write_line("And that you have permission to access VMs.\n")
        
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop()
    
    def _vm_info_helper(self, output_log: OutputLog) -> None:
        """Show VM info - lists all VMs and their details from both sessions."""
        if not shutil.which("virsh"):
            output_log.write_line("Error: virsh command not found.\n")
            output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
            return
        
        output_log.write_line("VM Information:\n\n")
        
        # Get VMs from both sessions with their session info
        all_vms_with_session = []
        for uri_name, uri in [("System", "qemu:///system"), ("Session", "qemu:///session")]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--all", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            all_vms_with_session.append((vm.strip(), uri_name, uri))
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        if all_vms_with_session:
            for vm_name, session_name, uri in all_vms_with_session:
                output_log.write_line(f"VM: {vm_name} ({session_name} session)\n")
                output_log.write_line("-" * 40 + "\n")
                try:
                    result = subprocess.run(
                        ["virsh", "-c", uri, "dominfo", vm_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        output_log.write_line(result.stdout)
                    else:
                        output_log.write_line(f"Error getting info for {vm_name}: {result.stderr}\n")
                except Exception as e:
                    output_log.write_line(f"Error: {e}\n")
                output_log.write_line("\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
        else:
            output_log.write_line("No VMs found. Use 'vm-list-all' to see all VMs.\n")
            output_log.write_line("Make sure libvirt is installed and VMs are defined.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _find_vm_session(self, vm_name: str) -> Optional[str]:
        """Find which session (system or session) a VM belongs to."""
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "dominfo", vm_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return uri
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        return None
    
    def _get_running_vms_with_session(self) -> List[Tuple[str, str]]:
        """Get list of running VMs with their session URI."""
        running_vms = []
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            running_vms.append((vm.strip(), uri))
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        return running_vms
    
    def _vm_start_helper(self, output_log: OutputLog) -> None:
        """Start VMs - attempts to start all stopped VMs."""
        output_log.write_line("Starting stopped VMs...\n\n")
        
        # Get all VMs with their session info
        all_vms_with_session = []
        for uri_name, uri in [("System", "qemu:///system"), ("Session", "qemu:///session")]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--all", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            all_vms_with_session.append((vm.strip(), uri))
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        # Get running VMs
        running_vms = set()
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            running_vms.add(vm.strip())
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        # Find stopped VMs
        stopped_vms = [(vm, uri) for vm, uri in all_vms_with_session if vm not in running_vms]
        
        if stopped_vms:
            for vm, uri in stopped_vms:
                output_log.write_line(f"Starting {vm}...\n")
                result = subprocess.run(
                    ["virsh", "-c", uri, "start", vm],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    output_log.write_line(f"✓ {vm} started successfully\n")
                else:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    output_log.write_line(f"✗ Failed to start {vm}\n")
                    output_log.write_line(f"  Error: {error_msg}\n")
                    # Check if it's a network issue and try to fix it
                    if "network" in error_msg.lower() and "not active" in error_msg.lower():
                        # Extract network name if possible
                        network_name = "default"
                        if "'" in error_msg:
                            # Try to extract network name from error message like "network 'default' is not active"
                            parts = error_msg.split("'")
                            if len(parts) >= 2:
                                network_name = parts[1]
                        
                        output_log.write_line(f"\n  Attempting to start network '{network_name}'...\n")
                        net_result = subprocess.run(
                            ["virsh", "-c", uri, "net-start", network_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if net_result.returncode == 0:
                            output_log.write_line(f"  ✓ Network '{network_name}' started. Retrying VM start...\n")
                            # Retry starting the VM
                            retry_result = subprocess.run(
                                ["virsh", "-c", uri, "start", vm],
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            if retry_result.returncode == 0:
                                output_log.write_line(f"  ✓ {vm} started successfully after network activation\n")
                            else:
                                output_log.write_line(f"  ✗ Still failed: {retry_result.stderr.strip()}\n")
                        else:
                            output_log.write_line(f"  ✗ Could not start network: {net_result.stderr.strip()}\n")
                            output_log.write_line(f"\n  Manual fix: virsh -c {uri} net-start {network_name}\n")
                            output_log.write_line(f"  Or enable autostart: virsh -c {uri} net-autostart {network_name}\n")
                output_log.write_line("\n")
        else:
            output_log.write_line("No stopped VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_shutdown_helper(self, output_log: OutputLog) -> None:
        """Shutdown VMs - gracefully shuts down all running VMs."""
        output_log.write_line("Shutting down running VMs...\n\n")
        running_vms = self._get_running_vms_with_session()
        
        if running_vms:
            for vm, uri in running_vms:
                output_log.write_line(f"Shutting down {vm}...\n")
                self._run_streaming(["virsh", "-c", uri, "shutdown", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_reboot_helper(self, output_log: OutputLog) -> None:
        """Reboot VMs - reboots all running VMs."""
        output_log.write_line("Rebooting running VMs...\n\n")
        running_vms = self._get_running_vms_with_session()
        
        if running_vms:
            for vm, uri in running_vms:
                output_log.write_line(f"Rebooting {vm}...\n")
                self._run_streaming(["virsh", "-c", uri, "reboot", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_force_stop_helper(self, output_log: OutputLog) -> None:
        """Force stop VMs - force stops all running VMs (dangerous)."""
        output_log.write_line("⚠️  WARNING: Force stop is dangerous and may cause data loss!\n\n")
        running_vms = self._get_running_vms_with_session()
        
        if running_vms:
            output_log.write_line("Force stopping running VMs...\n\n")
            for vm, uri in running_vms:
                output_log.write_line(f"Force stopping {vm}...\n")
                self._run_streaming(["virsh", "-c", uri, "destroy", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_suspend_helper(self, output_log: OutputLog) -> None:
        """Suspend VMs - suspends all running VMs."""
        output_log.write_line("Suspending running VMs...\n\n")
        running_vms = self._get_running_vms_with_session()
        
        if running_vms:
            for vm, uri in running_vms:
                output_log.write_line(f"Suspending {vm}...\n")
                self._run_streaming(["virsh", "-c", uri, "suspend", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_resume_helper(self, output_log: OutputLog) -> None:
        """Resume VMs - resumes all suspended VMs."""
        output_log.write_line("Resuming suspended VMs...\n\n")
        
        # Get all VMs with their session info
        all_vms_with_session = []
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--all", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            all_vms_with_session.append((vm.strip(), uri))
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        # Get running VMs
        running_vms = set()
        for uri in ["qemu:///system", "qemu:///session"]:
            try:
                result = subprocess.run(
                    ["virsh", "-c", uri, "list", "--name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for vm in result.stdout.strip().split("\n"):
                        if vm.strip():
                            running_vms.add(vm.strip())
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                continue
        
        # Try to detect suspended VMs by checking their state
        suspended_vms = []
        for vm, uri in all_vms_with_session:
            if vm not in running_vms:
                try:
                    result = subprocess.run(
                        ["virsh", "-c", uri, "dominfo", vm],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        if "paused" in result.stdout.lower() or "suspended" in result.stdout.lower():
                            suspended_vms.append((vm, uri))
                except:
                    pass
        
        if suspended_vms:
            for vm, uri in suspended_vms:
                output_log.write_line(f"Resuming {vm}...\n")
                self._run_streaming(["virsh", "-c", uri, "resume", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No suspended VMs found.\n")
            stopped_vms = [(vm, uri) for vm, uri in all_vms_with_session if vm not in running_vms]
            if stopped_vms:
                output_log.write_line("Stopped VMs (use 'vm-start' to start them):\n")
                for vm, uri in stopped_vms:
                    output_log.write_line(f"  - {vm}\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_console_helper(self, output_log: OutputLog) -> None:
        """VM Console - shows running VMs (console is interactive, so instructions only)."""
        if not shutil.which("virsh"):
            output_log.write_line("Error: virsh command not found.\n")
            output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
            return
        
        output_log.write_line("Running VMs:\n\n")
        running_vms = self._get_running_vms()
        
        if running_vms:
            output_log.write_line("To open console for a VM, run from terminal:\n")
            for vm in running_vms:
                output_log.write_line(f"  virsh console {vm}\n")
            output_log.write_line("\nNote: Console access requires the VM to be configured for serial console.\n")
            output_log.write_line("Console is interactive and cannot be opened from this TUI.\n")
        else:
            output_log.write_line("No running VMs found.\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop()
    
    def _run_vm_stats(self, output_log: OutputLog) -> None:
        """Show resource usage statistics for VMs."""
        output_log.write_line("VM Resource Statistics:\n\n")
        
        try:
            vms = self._get_running_vms()
            
            if vms:
                for vm in vms:
                    output_log.write_line(f"  {vm}:\n")
                    try:
                        # Get VM info
                        info_result = subprocess.run(
                            ["virsh", "dominfo", vm],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if info_result.returncode == 0:
                            for line in info_result.stdout.split("\n"):
                                if "CPU(s)" in line or "Max memory" in line or "Used memory" in line:
                                    output_log.write_line(f"    {line.strip()}\n")
                    except Exception:
                        pass
                    output_log.write_line("\n")
            else:
                output_log.write_line("  No running VMs found.\n")
        except FileNotFoundError:
            output_log.write_line("  Error: virsh command not found. Is libvirt installed?\n")
        except Exception as e:
            output_log.write_line(f"  Error: {e}\n")
        
        output_log.write_line("\n" + "-" * 60 + "\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop_success()
    
    def _vm_create_helper(self, output_log: OutputLog) -> None:
        """Create a new VM - launches interactive wizard."""
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop()
        
        # Check if libvirt tools are available
        if not shutil.which("virsh"):
            output_log.write_line("Error: virsh command not found.\n")
            output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
            output_log.write_line("Or install via NixOS: services.libvirtd.enable = true;\n")
            return
        
        # Launch the VM creation wizard
        self.push_screen(VMCreateWizard(self.flake_path, output_log))


# =============================================================================
# Entry Point
# =============================================================================

def _get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""


def _check_and_update_script() -> bool:
    """
    Perform git pull in background and check if manage.py has changed.
    Returns True if the script should be relaunched, False otherwise.
    """
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    
    # Get current hash of manage.py
    current_hash = _get_file_hash(script_path)
    
    # Perform git pull in background (non-blocking)
    pull_complete = threading.Event()
    pull_result = {"success": False}
    
    def git_pull_thread():
        """Thread function to perform git pull."""
        try:
            pull_process = subprocess.run(
                ["git", "pull"],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            pull_result["success"] = (pull_process.returncode == 0)
        except subprocess.TimeoutExpired:
            pull_result["success"] = False
        except Exception:
            pull_result["success"] = False
        finally:
            pull_complete.set()
    
    # Start git pull in background thread
    pull_thread = threading.Thread(target=git_pull_thread, daemon=True)
    pull_thread.start()
    
    # Wait a short time for git pull to complete (max 3 seconds)
    # This allows quick updates without blocking too long
    pull_complete.wait(timeout=3.0)
    
    # Check if manage.py has changed (only if git pull completed)
    if pull_complete.is_set() and pull_result["success"]:
        new_hash = _get_file_hash(script_path)
        
        if new_hash != current_hash and new_hash != "":
            # Script has been updated
            print("\n" + "=" * 60)
            print("⚠️  UPDATE DETECTED")
            print("=" * 60)
            print(f"A new version of {script_path.name} has been downloaded.")
            print("The script will be relaunched with the new version.")
            print("\nPress Enter to continue...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                # Handle cases where stdin is not available
                pass
            
            # Relaunch the script
            try:
                os.execv(script_path, [str(script_path)] + sys.argv[1:])
            except Exception:
                # If execv fails, try subprocess
                try:
                    subprocess.run([sys.executable, str(script_path)] + sys.argv[1:])
                    sys.exit(0)
                except Exception:
                    pass
            
            return True
    
    return False


def main():
    """Main entry point."""
    # Check for updates and relaunch if needed
    if _check_and_update_script():
        # Script was relaunched, this code won't execute
        return
    
    app = ManageApp()
    app.run()


if __name__ == "__main__":
    main()
