#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.rich python3Packages.textual
"""
manage.py - System Management Console
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
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header, Footer, Static, Label, Button, Log, 
        Tab, TabbedContent, TabPane
    )
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.binding import Binding
    from textual import on, events
    from textual.message import Message
    from textual.reactive import reactive
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
# Action Definitions by Category
# =============================================================================

TABS = [
    ("nixos", "NixOS", "❄️"),
    ("docker", "Docker", "🐳"),
    ("system", "System", "🖥️"),
    ("git", "Git", "📂"),
    ("network", "Network", "🌐"),
    ("services", "Services", "⚙️"),
    ("storage", "Storage", "💾"),
    ("vm", "Virtual Machines", "💻"),
]

ACTIONS = {
    "nixos": [
        ("switch", "Switch Configuration", "Apply NixOS configuration immediately using nixos-rebuild switch", False, True),
        ("boot", "Boot Configuration", "Build and set configuration for next boot without activating", False, True),
        ("build", "Build Configuration", "Build the NixOS configuration without applying it", False, True),
        ("dry-run", "Dry Run", "Show what changes would be made without applying them", False, True),
        ("update", "Update Flake Inputs", "Update all flake inputs to their latest versions", False, False),
        ("update-nixpkgs", "Update Nixpkgs", "Update only the nixpkgs input", False, False),
        ("rebuild-all", "Rebuild All Machines", "Build configurations for all defined machines", False, False),
        ("status", "System Status", "Show current and available NixOS generations", False, True),
        ("health", "Health Check", "Run comprehensive system health diagnostics", False, False),
        ("gc", "Garbage Collection", "Remove old generations and free up disk space", False, False),
        ("list", "List Machines", "Show all available machine configurations", False, False),
        ("rollback", "Rollback", "Roll back to the previous system generation", True, True),
        ("diff", "Show Diff", "Show differences between current and new configuration", False, True),
    ],
    "docker": [
        ("docker-ps", "List Containers", "Show all running Docker containers", False, False),
        ("docker-ps-all", "List All Containers", "Show all containers including stopped ones", False, False),
        ("docker-images", "List Images", "Show all Docker images on the system", False, False),
        ("docker-compose-up", "Compose Up", "Start all services defined in docker-compose.yml", False, False),
        ("docker-compose-down", "Compose Down", "Stop and remove all composed services", False, False),
        ("docker-compose-logs", "Compose Logs", "View logs from all composed services", False, False),
        ("docker-prune", "System Prune", "Remove unused containers, networks, and images", True, False),
        ("docker-prune-all", "Full Prune", "Remove all unused data including volumes", True, False),
        ("docker-stats", "Container Stats", "Show real-time resource usage of containers", False, False),
        ("docker-networks", "List Networks", "Show all Docker networks", False, False),
        ("docker-volumes", "List Volumes", "Show all Docker volumes", False, False),
        ("docker-restart-all", "Restart All", "Restart all running containers", True, False),
    ],
    "system": [
        ("sys-info", "System Info", "Display detailed system information", False, False),
        ("sys-uptime", "Uptime", "Show system uptime and load averages", False, False),
        ("sys-memory", "Memory Usage", "Display memory and swap usage statistics", False, False),
        ("sys-cpu", "CPU Info", "Show CPU information and current usage", False, False),
        ("sys-processes", "Top Processes", "List processes sorted by resource usage", False, False),
        ("sys-services", "Failed Services", "Show any failed systemd services", False, False),
        ("sys-logs", "System Logs", "View recent system journal logs", False, False),
        ("sys-boot-logs", "Boot Logs", "View logs from the current boot", False, False),
        ("sys-reboot", "Reboot System", "Safely reboot the system", True, False),
        ("sys-shutdown", "Shutdown", "Safely shutdown the system", True, False),
        ("sys-suspend", "Suspend", "Suspend the system to RAM", False, False),
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
        ("net-status", "Network Status", "Show network interface status", False, False),
        ("net-ip", "IP Addresses", "Display all IP addresses", False, False),
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
        ("vm-list", "List VMs", "Show all virtual machines and their status", False, False),
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

MACHINES = ["brian-laptop", "superheavy", "docker", "backup"]


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
                 category: str, index: int, **kwargs):
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
    
    def __init__(self, category: str, **kwargs):
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
    
    def __init__(self, **kwargs):
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
        self.update("[green]✓[/green]")
    
    def _update(self) -> None:
        """Update the spinner frame."""
        if self._spinning:
            frame = self.SPINNER_FRAMES[self._frame_index % len(self.SPINNER_FRAMES)]
            self.update(f"[cyan]{frame}[/cyan]")
            self._frame_index += 1
            self.set_timer(0.1, self._update)


class OutputLog(Log):
    """Widget for displaying command output."""
    
    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup tags from text."""
        import re
        return re.sub(r'\[/?[^\]]+\]', '', text)
    
    def write_line(self, content: str) -> None:
        """Write a line, stripping markup."""
        if isinstance(content, str):
            content = self._strip_markup(content)
        self.write(content)


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
        Binding("1", "tab_1", "NixOS", show=False),
        Binding("2", "tab_2", "Docker", show=False),
        Binding("3", "tab_3", "System", show=False),
        Binding("4", "tab_4", "Git", show=False),
        Binding("5", "tab_5", "Network", show=False),
        Binding("6", "tab_6", "Services", show=False),
        Binding("7", "tab_7", "Storage", show=False),
        Binding("m", "cycle_machine", "Machine"),
        Binding("c", "clear_output", "Clear"),
    ]
    
    current_tab = reactive("nixos")
    
    def __init__(self):
        super().__init__()
        self.flake_path = Path(__file__).parent.absolute()
        self.machines_list = MACHINES
        self.current_machine = self._detect_current_machine()
        self.machine_index = 0
        if self.current_machine in self.machines_list:
            self.machine_index = self.machines_list.index(self.current_machine)
        self._current_process = None
        self._current_process_exit_code = None
    
    def _detect_current_machine(self) -> Optional[str]:
        """Detect the current machine from hostname."""
        try:
            hostname = subprocess.check_output(["hostname"], text=True).strip()
            if hostname in self.machines_list:
                return hostname
        except Exception:
            pass
        return self.machines_list[0] if self.machines_list else None
    
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
                    yield ActionList("nixos", id="actions-current")
                    
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
        
        # Update the action list to show actions for the new tab
        action_panel = self.query_one("#action-panel", Vertical)
        
        # Try to find and remove existing action list
        try:
            current_action_list = action_panel.query_one("#actions-current", ActionList)
            current_action_list.remove()
            # Schedule mounting new list after removal completes
            self.call_after_refresh(self._mount_new_action_list, tab_id)
        except Exception:
            # No existing action list, mount immediately
            self._mount_new_action_list(tab_id)
    
    def _mount_new_action_list(self, tab_id: str) -> None:
        """Mount a new action list for the given tab."""
        action_panel = self.query_one("#action-panel", Vertical)
        new_action_list = ActionList(tab_id, id="actions-current")
        action_panel.mount(new_action_list)
        # Set focus on the new action list after it's fully mounted
        self.call_after_refresh(lambda: self.set_focus(new_action_list))
        self._update_description()
    
    def action_navigate_up(self) -> None:
        action_list = self._get_current_action_list()
        if action_list:
            action_list.select_previous()
            self._update_description()
    
    def action_navigate_down(self) -> None:
        action_list = self._get_current_action_list()
        if action_list:
            action_list.select_next()
            self._update_description()
    
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
        output_log = self.query_one("#output-log", OutputLog)
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
        output_log = self.query_one("#output-log", OutputLog)
        spinner = self.query_one("#spinner", Spinner)
        
        # Confirmation for dangerous actions
        if dangerous:
            # For now, just warn - in a full implementation you'd use a modal
            spinner.stop()
            output_log.clear()
            output_log.write_line(f"⚠️  WARNING: '{title}' is a dangerous operation!\n")
            output_log.write_line("This command has been blocked for safety.\n")
            output_log.write_line("To execute dangerous commands, run them directly from the terminal.\n")
            output_log.write_line("Command that would have been run:\n")
            # Show what command would have been executed
            if requires_machine:
                output_log.write_line(f"  Machine: {self.current_machine}\n")
            return
        
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
        """Run the actual command for an action."""
        
        # NixOS commands
        if action_id == "switch":
            self._run_streaming(["sudo", "nixos-rebuild", "switch", "--flake", f".#{machine}"], output_log)
        elif action_id == "boot":
            self._run_streaming(["sudo", "nixos-rebuild", "boot", "--flake", f".#{machine}"], output_log)
        elif action_id == "build":
            self._run_streaming(["nix", "build", f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                                "--extra-experimental-features", "nix-command flakes"], output_log)
        elif action_id == "dry-run":
            self._run_streaming(["sudo", "nixos-rebuild", "dry-run", "--flake", f".#{machine}"], output_log)
        elif action_id == "update":
            self._run_streaming(["nix", "flake", "update", "--extra-experimental-features", "nix-command flakes"], output_log)
        elif action_id == "update-nixpkgs":
            self._run_streaming(["nix", "flake", "update", "nixpkgs", "--extra-experimental-features", "nix-command flakes"], output_log)
        elif action_id == "rebuild-all":
            self._rebuild_all_machines(output_log)
        elif action_id == "status":
            self._run_streaming(["nixos-rebuild", "list-generations"], output_log)
        elif action_id == "health":
            self._run_health_check(output_log)
        elif action_id == "gc":
            self._run_streaming(["sudo", "nix-collect-garbage", "-d"], output_log)
        elif action_id == "list":
            self._list_machines(output_log)
        elif action_id == "rollback":
            self._run_streaming(["sudo", "nixos-rebuild", "switch", "--rollback"], output_log)
        elif action_id == "diff":
            self._run_streaming(["nix", "build", f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                                "--extra-experimental-features", "nix-command flakes", "-o", "result"], output_log)
            self._run_streaming(["nvd", "diff", "/run/current-system", "result"], output_log)
        
        # Docker commands
        elif action_id == "docker-ps":
            self._run_streaming(["docker", "ps"], output_log)
        elif action_id == "docker-ps-all":
            self._run_streaming(["docker", "ps", "-a"], output_log)
        elif action_id == "docker-images":
            self._run_streaming(["docker", "images"], output_log)
        elif action_id == "docker-compose-up":
            self._run_streaming(["docker", "compose", "up", "-d"], output_log)
        elif action_id == "docker-compose-down":
            self._run_streaming(["docker", "compose", "down"], output_log)
        elif action_id == "docker-compose-logs":
            self._run_streaming(["docker", "compose", "logs", "--tail=50"], output_log)
        elif action_id == "docker-prune":
            self._run_streaming(["docker", "system", "prune", "-f"], output_log)
        elif action_id == "docker-prune-all":
            self._run_streaming(["docker", "system", "prune", "-af", "--volumes"], output_log)
        elif action_id == "docker-stats":
            self._run_streaming(["docker", "stats", "--no-stream"], output_log)
        elif action_id == "docker-networks":
            self._run_streaming(["docker", "network", "ls"], output_log)
        elif action_id == "docker-volumes":
            self._run_streaming(["docker", "volume", "ls"], output_log)
        elif action_id == "docker-restart-all":
            self._run_streaming(["sh", "-c", "docker restart $(docker ps -q)"], output_log, shell=False)
        
        # System commands
        elif action_id == "sys-info":
            self._run_system_info(output_log)
        elif action_id == "sys-uptime":
            self._run_streaming(["uptime"], output_log)
        elif action_id == "sys-memory":
            self._run_streaming(["free", "-h"], output_log)
        elif action_id == "sys-cpu":
            self._run_streaming(["lscpu"], output_log)
        elif action_id == "sys-processes":
            self._run_streaming(["ps", "aux", "--sort=-%mem"], output_log)
        elif action_id == "sys-services":
            self._run_streaming(["systemctl", "--failed"], output_log)
        elif action_id == "sys-logs":
            self._run_streaming(["journalctl", "-n", "50", "--no-pager"], output_log)
        elif action_id == "sys-boot-logs":
            self._run_streaming(["journalctl", "-b", "-n", "50", "--no-pager"], output_log)
        elif action_id == "sys-reboot":
            self._run_streaming(["sudo", "systemctl", "reboot"], output_log)
        elif action_id == "sys-shutdown":
            self._run_streaming(["sudo", "systemctl", "poweroff"], output_log)
        elif action_id == "sys-suspend":
            self._run_streaming(["systemctl", "suspend"], output_log)
        
        # Git commands
        elif action_id == "git-status":
            self._run_streaming(["git", "status"], output_log)
        elif action_id == "git-pull":
            self._run_streaming(["git", "pull"], output_log)
        elif action_id == "git-push":
            self._run_streaming(["git", "push"], output_log)
        elif action_id == "git-log":
            self._run_streaming(["git", "log", "--oneline", "-20"], output_log)
        elif action_id == "git-diff":
            self._run_streaming(["git", "diff"], output_log)
        elif action_id == "git-branch":
            self._run_streaming(["git", "branch", "-a"], output_log)
        elif action_id == "git-stash":
            self._run_streaming(["git", "stash"], output_log)
        elif action_id == "git-stash-pop":
            self._run_streaming(["git", "stash", "pop"], output_log)
        elif action_id == "git-fetch":
            self._run_streaming(["git", "fetch", "--all"], output_log)
        elif action_id == "git-reset":
            self._run_streaming(["git", "reset", "--hard", "HEAD"], output_log)
        elif action_id == "git-clean":
            self._run_streaming(["git", "clean", "-fd"], output_log)
        
        # Network commands
        elif action_id == "net-status":
            self._run_streaming(["ip", "link", "show"], output_log)
        elif action_id == "net-ip":
            self._run_streaming(["ip", "addr", "show"], output_log)
        elif action_id == "net-connections":
            self._run_streaming(["ss", "-tuln"], output_log)
        elif action_id == "net-ports":
            self._run_streaming(["ss", "-tlnp"], output_log)
        elif action_id == "net-ping":
            self._run_ping_test(output_log)
        elif action_id == "net-dns":
            self._run_dns_test(output_log)
        elif action_id == "net-trace":
            self._run_streaming(["traceroute", "-m", "15", "8.8.8.8"], output_log)
        elif action_id == "net-wifi":
            self._run_streaming(["nmcli", "device", "wifi", "list"], output_log)
        elif action_id == "net-firewall":
            self._run_streaming(["sudo", "iptables", "-L", "-n"], output_log)
        elif action_id == "net-bandwidth":
            self._run_streaming(["speedtest-cli", "--simple"], output_log)
        
        # Services commands
        elif action_id == "svc-list":
            self._run_streaming(["systemctl", "list-units", "--type=service", "--no-pager"], output_log)
        elif action_id == "svc-running":
            self._run_streaming(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], output_log)
        elif action_id == "svc-failed":
            self._run_streaming(["systemctl", "--failed", "--no-pager"], output_log)
        elif action_id == "svc-timers":
            self._run_streaming(["systemctl", "list-timers", "--no-pager"], output_log)
        elif action_id == "svc-reload":
            self._run_streaming(["sudo", "systemctl", "daemon-reload"], output_log)
        elif action_id == "svc-nginx":
            self._run_streaming(["systemctl", "status", "nginx", "--no-pager"], output_log)
        elif action_id == "svc-postgres":
            self._run_streaming(["systemctl", "status", "postgresql", "--no-pager"], output_log)
        elif action_id == "svc-redis":
            self._run_streaming(["systemctl", "status", "redis", "--no-pager"], output_log)
        elif action_id == "svc-ssh":
            self._run_streaming(["systemctl", "status", "sshd", "--no-pager"], output_log)
        elif action_id == "svc-docker":
            self._run_streaming(["systemctl", "status", "docker", "--no-pager"], output_log)
        
        # Storage commands
        elif action_id == "disk-usage":
            self._run_streaming(["df", "-h"], output_log)
        elif action_id == "disk-free":
            self._run_streaming(["df", "-h", "--output=target,avail,pcent"], output_log)
        elif action_id == "disk-mounts":
            self._run_streaming(["mount"], output_log)
        elif action_id == "disk-io":
            self._run_streaming(["iostat", "-x", "1", "1"], output_log)
        elif action_id == "disk-largest":
            self._run_streaming(["sudo", "sh", "-c", "du -ah / --max-depth=3 2>/dev/null | sort -rh | head -20"], output_log, shell=False)
        elif action_id == "disk-inodes":
            self._run_streaming(["df", "-i"], output_log)
        elif action_id == "zfs-status":
            self._run_streaming(["zpool", "status"], output_log)
        elif action_id == "zfs-list":
            self._run_streaming(["zfs", "list"], output_log)
        elif action_id == "zfs-snapshots":
            self._run_streaming(["zfs", "list", "-t", "snapshot"], output_log)
        elif action_id == "smart-status":
            self._run_smart_status(output_log)
        
        # Virtual Machine commands
        elif action_id == "vm-list":
            # Check if virsh is available first
            if not shutil.which("virsh"):
                output_log.write_line("Error: virsh command not found.\n")
                output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
                spinner = self.query_one("#spinner", Spinner)
                spinner.stop()
            else:
                self._run_streaming(["virsh", "list"], output_log)
        elif action_id == "vm-list-all":
            # Check if virsh is available first
            if not shutil.which("virsh"):
                output_log.write_line("Error: virsh command not found.\n")
                output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
                spinner = self.query_one("#spinner", Spinner)
                spinner.stop()
            else:
                self._run_streaming(["virsh", "list", "--all"], output_log)
        elif action_id == "vm-info":
            self._vm_info_helper(output_log)
        elif action_id == "vm-start":
            self._vm_start_helper(output_log)
        elif action_id == "vm-shutdown":
            self._vm_shutdown_helper(output_log)
        elif action_id == "vm-reboot":
            self._vm_reboot_helper(output_log)
        elif action_id == "vm-force-stop":
            self._vm_force_stop_helper(output_log)
        elif action_id == "vm-suspend":
            self._vm_suspend_helper(output_log)
        elif action_id == "vm-resume":
            self._vm_resume_helper(output_log)
        elif action_id == "vm-console":
            self._vm_console_helper(output_log)
        elif action_id == "vm-stats":
            self._run_vm_stats(output_log)
        elif action_id == "vm-networks":
            self._run_streaming(["virsh", "net-list", "--all"], output_log)
        elif action_id == "vm-pools":
            self._run_streaming(["virsh", "pool-list", "--all"], output_log)
        elif action_id == "vm-domains":
            self._run_streaming(["virsh", "list", "--all"], output_log)
        
        else:
            output_log.write_line(f"Unknown action: {action_id}\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _run_streaming(self, cmd: List[str], output_log: OutputLog, shell: bool = False) -> None:
        """Run a command and stream output to the log."""
        def run_in_thread():
            try:
                # Log the command being executed
                cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                self.call_from_thread(output_log.write_line, f"Running: {cmd_str}\n\n")
                
                if shell:
                    cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                    process = subprocess.Popen(
                        cmd_str,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        cwd=self.flake_path,
                        text=True,
                        bufsize=1
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
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
                
                # Stop spinner and show success/failure indicator
                spinner = self.query_one("#spinner", Spinner)
                if process.returncode == 0:
                    self.call_from_thread(spinner.stop_success)
                    if not output_received:
                        self.call_from_thread(output_log.write_line, "Command completed (no output)\n")
                else:
                    self.call_from_thread(spinner.stop)
                    self.call_from_thread(output_log.write_line, f"✗ Command failed with exit code {process.returncode}\n")
                    if not output_received:
                        self.call_from_thread(output_log.write_line, "No output was produced. The command may have failed silently.\n")
                
            except FileNotFoundError:
                spinner = self.query_one("#spinner", Spinner)
                self.call_from_thread(spinner.stop)
                cmd_name = cmd[0] if isinstance(cmd, list) and len(cmd) > 0 else str(cmd)
                self.call_from_thread(output_log.write_line, f"✗ Error: Command not found: {cmd_name}\n")
                self.call_from_thread(output_log.write_line, "Make sure the command is installed and available in PATH.\n")
            except Exception as e:
                spinner = self.query_one("#spinner", Spinner)
                self.call_from_thread(spinner.stop)
                self.call_from_thread(output_log.write_line, f"✗ Error executing command: {e}\n")
                import traceback
                self.call_from_thread(output_log.write_line, f"Traceback:\n{traceback.format_exc()}\n")
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def _rebuild_all_machines(self, output_log: OutputLog) -> None:
        """Rebuild all machine configurations."""
        def run_in_thread():
            for machine in self.machines_list:
                self.call_from_thread(output_log.write_line, f"\nBuilding {machine}...\n")
                try:
                    result = subprocess.run(
                        ["nix", "build", f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                         "--extra-experimental-features", "nix-command flakes"],
                        cwd=self.flake_path,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.call_from_thread(output_log.write_line, f"✓ {machine} built successfully\n")
                    else:
                        self.call_from_thread(output_log.write_line, f"✗ {machine} failed:\n{result.stderr}\n")
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
        output_log.write_line("\n" + "-" * 60 + "\n")
        spinner = self.query_one("#spinner", Spinner)
        spinner.stop_success()
    
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
            
            output_log.write_line("\n" + "-" * 60 + "\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop_success()
    
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
        """Get list of VMs. Returns empty list if virsh is not available."""
        if not shutil.which("virsh"):
            return []
        try:
            cmd = ["virsh", "list", "--name"]
            if all_vms:
                cmd.append("--all")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return [vm.strip() for vm in result.stdout.strip().split("\n") if vm.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        return []
    
    def _get_running_vms(self) -> List[str]:
        """Get list of running VMs."""
        if not shutil.which("virsh"):
            return []
        try:
            result = subprocess.run(
                ["virsh", "list", "--name"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return [vm.strip() for vm in result.stdout.strip().split("\n") if vm.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        return []
    
    def _vm_info_helper(self, output_log: OutputLog) -> None:
        """Show VM info - lists all VMs and their details."""
        if not shutil.which("virsh"):
            output_log.write_line("Error: virsh command not found.\n")
            output_log.write_line("Make sure libvirt is installed: nix-shell -p libvirt\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
            return
        
        output_log.write_line("VM Information:\n\n")
        vms = self._get_vm_list(all_vms=True)
        if vms:
            for vm in vms:
                output_log.write_line(f"VM: {vm}\n")
                output_log.write_line("-" * 40 + "\n")
                try:
                    result = subprocess.run(
                        ["virsh", "dominfo", vm],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        output_log.write_line(result.stdout)
                    else:
                        output_log.write_line(f"Error getting info for {vm}: {result.stderr}\n")
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
    
    def _vm_start_helper(self, output_log: OutputLog) -> None:
        """Start VMs - attempts to start all stopped VMs."""
        output_log.write_line("Starting stopped VMs...\n\n")
        all_vms = self._get_vm_list(all_vms=True)
        running_vms = self._get_running_vms()
        stopped_vms = [vm for vm in all_vms if vm not in running_vms]
        
        if stopped_vms:
            for vm in stopped_vms:
                output_log.write_line(f"Starting {vm}...\n")
                self._run_streaming(["virsh", "start", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No stopped VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_shutdown_helper(self, output_log: OutputLog) -> None:
        """Shutdown VMs - gracefully shuts down all running VMs."""
        output_log.write_line("Shutting down running VMs...\n\n")
        running_vms = self._get_running_vms()
        
        if running_vms:
            for vm in running_vms:
                output_log.write_line(f"Shutting down {vm}...\n")
                self._run_streaming(["virsh", "shutdown", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_reboot_helper(self, output_log: OutputLog) -> None:
        """Reboot VMs - reboots all running VMs."""
        output_log.write_line("Rebooting running VMs...\n\n")
        running_vms = self._get_running_vms()
        
        if running_vms:
            for vm in running_vms:
                output_log.write_line(f"Rebooting {vm}...\n")
                self._run_streaming(["virsh", "reboot", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_force_stop_helper(self, output_log: OutputLog) -> None:
        """Force stop VMs - force stops all running VMs (dangerous)."""
        output_log.write_line("⚠️  WARNING: Force stop is dangerous and may cause data loss!\n\n")
        running_vms = self._get_running_vms()
        
        if running_vms:
            output_log.write_line("Force stopping running VMs...\n\n")
            for vm in running_vms:
                output_log.write_line(f"Force stopping {vm}...\n")
                self._run_streaming(["virsh", "destroy", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_suspend_helper(self, output_log: OutputLog) -> None:
        """Suspend VMs - suspends all running VMs."""
        output_log.write_line("Suspending running VMs...\n\n")
        running_vms = self._get_running_vms()
        
        if running_vms:
            for vm in running_vms:
                output_log.write_line(f"Suspending {vm}...\n")
                self._run_streaming(["virsh", "suspend", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No running VMs found.\n")
            spinner = self.query_one("#spinner", Spinner)
            spinner.stop()
    
    def _vm_resume_helper(self, output_log: OutputLog) -> None:
        """Resume VMs - resumes all suspended VMs."""
        output_log.write_line("Resuming suspended VMs...\n\n")
        all_vms = self._get_vm_list(all_vms=True)
        running_vms = self._get_running_vms()
        
        # Try to detect suspended VMs by checking their state
        suspended_vms = []
        for vm in all_vms:
            if vm not in running_vms:
                try:
                    result = subprocess.run(
                        ["virsh", "dominfo", vm],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        if "paused" in result.stdout.lower() or "suspended" in result.stdout.lower():
                            suspended_vms.append(vm)
                except:
                    pass
        
        if suspended_vms:
            for vm in suspended_vms:
                output_log.write_line(f"Resuming {vm}...\n")
                self._run_streaming(["virsh", "resume", vm], output_log)
                output_log.write_line("\n")
        else:
            output_log.write_line("No suspended VMs found.\n")
            stopped_vms = [vm for vm in all_vms if vm not in running_vms]
            if stopped_vms:
                output_log.write_line("Stopped VMs (use 'vm-start' to start them):\n")
                for vm in stopped_vms:
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


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    app = ManageApp()
    app.run()


if __name__ == "__main__":
    main()
