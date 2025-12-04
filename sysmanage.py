#!/usr/bin/env python3
"""
SysManage - A TUI System Management Tool for NixOS
Fast, beautiful, and easy to navigate system management.
"""

import asyncio
import os
import subprocess
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    OptionList,
    RichLog,
    Static,
)
from textual.widgets.option_list import Option
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.style import Style
import re


# ============================================================================
# Configuration
# ============================================================================

DOTFILES_PATH = Path.home() / "dotfiles"
HOSTNAME = socket.gethostname()

# NixOS commands
NIXOS_COMMANDS = {
    "switch": f"sudo nixos-rebuild switch --flake {DOTFILES_PATH}#{HOSTNAME}",
    "boot": f"sudo nixos-rebuild boot --flake {DOTFILES_PATH}#{HOSTNAME}",
    "test": f"sudo nixos-rebuild test --flake {DOTFILES_PATH}#{HOSTNAME}",
    "build": f"nixos-rebuild build --flake {DOTFILES_PATH}#{HOSTNAME}",
    "update": f"cd {DOTFILES_PATH} && nix flake update",
    "gc": "sudo nix-collect-garbage -d",
    "optimise": "sudo nix-store --optimise",
}

# Docker commands
DOCKER_COMMANDS = {
    "ps": "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'",
    "images": "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'",
    "prune": "docker system prune -af",
    "prune_volumes": "docker system prune -af --volumes",
}

# Log commands
LOG_COMMANDS = {
    "system": "journalctl -f -n 100",
    "kernel": "journalctl -f -n 100 -k",
    "docker": "journalctl -f -n 100 -u docker",
    "nginx": "journalctl -f -n 100 -u nginx",
    "sshd": "journalctl -f -n 100 -u sshd",
    "tailscale": "journalctl -f -n 100 -u tailscaled",
    "boot": "journalctl -b -n 200",
}


# ============================================================================
# Custom CSS
# ============================================================================

CSS = """
Screen {
    background: #0f0f14;
}

#main-container {
    width: 100%;
    height: 100%;
}

/* Top tabs bar */
#tabs-bar {
    height: 3;
    width: 100%;
    background: #1a1b26;
    padding: 0 2;
    align: left middle;
}

.tab {
    min-width: 16;
    height: 3;
    margin: 0;
    padding: 0 2;
    border: none;
    background: transparent;
    color: #565f89;
    text-style: none;
}

.tab:hover {
    color: #a9b1d6;
    background: transparent;
}

.tab:focus {
    text-style: none;
}

.tab.active {
    color: #c0caf5;
    text-style: bold;
    background: #0f0f14;
    border-top: tall #7aa2f7;
}

/* Content wrapper */
#content-wrapper {
    height: 1fr;
}

/* Sidebar with commands */
#sidebar {
    width: 22;
    background: #16161e;
    border-right: tall #292e42;
    padding: 1;
}

#sidebar-title {
    text-style: bold;
    color: #7aa2f7;
    padding-bottom: 1;
    border-bottom: solid #292e42;
    margin-bottom: 1;
    text-align: center;
}

/* Sidebar buttons */
#sidebar Button {
    width: 100%;
    height: 3;
    margin-bottom: 1;
    border: none;
}

#sidebar .cmd-success {
    background: #9ece6a;
    color: #0f0f14;
}

#sidebar .cmd-success:hover {
    background: #b9f27c;
}

#sidebar .cmd-info {
    background: #7aa2f7;
    color: #0f0f14;
}

#sidebar .cmd-info:hover {
    background: #a9c4ff;
}

#sidebar .cmd-warning {
    background: #e0af68;
    color: #0f0f14;
}

#sidebar .cmd-warning:hover {
    background: #ffc777;
}

#sidebar .cmd-danger {
    background: #f7768e;
    color: #0f0f14;
}

#sidebar .cmd-danger:hover {
    background: #ff9e9e;
}

.sidebar-section {
    display: none;
    height: auto;
}

.sidebar-section.visible {
    display: block;
}

.section-label {
    color: #565f89;
    padding: 1 0;
    text-align: center;
}

/* Main output area */
#output-area {
    width: 1fr;
    height: 100%;
    padding: 1;
    background: #0f0f14;
}

/* RichLog output panels */
RichLog {
    height: 1fr;
    border: round #292e42;
    background: #16161e;
    padding: 1;
    scrollbar-background: #16161e;
    scrollbar-color: #3d59a1;
    scrollbar-color-hover: #7aa2f7;
    scrollbar-color-active: #7aa2f7;
}

.output-panel {
    display: none;
    height: 100%;
}

.output-panel.visible {
    display: block;
}

/* Option list for docker containers */
#docker-containers {
    height: 10;
    border: round #292e42;
    background: #16161e;
    margin-bottom: 1;
}

#docker-containers:focus {
    border: round #7aa2f7;
}

#docker-containers > .option-list--option {
    padding: 0 1;
}

#docker-containers > .option-list--option-highlighted {
    background: #292e42;
}

/* Confirmation dialog */
ConfirmDialog {
    align: center middle;
}

#confirm-container {
    width: 50;
    height: auto;
    background: #16161e;
    border: round #f7768e;
    padding: 1 2;
}

#confirm-title {
    text-style: bold;
    color: #f7768e;
    text-align: center;
    padding-bottom: 1;
    border-bottom: solid #292e42;
}

#confirm-message {
    padding: 1 0;
    text-align: center;
    color: #c0caf5;
}

#confirm-buttons {
    padding-top: 1;
    align: center middle;
}

#confirm-buttons Button {
    margin: 0 1;
    min-width: 12;
}

/* Header styling */
Header {
    background: #16161e;
    color: #7aa2f7;
}

/* Footer styling */
Footer {
    background: #16161e;
}

Footer > .footer--key {
    background: #3d59a1;
    color: #c0caf5;
}

Footer > .footer--description {
    color: #565f89;
}
"""


# ============================================================================
# Screens
# ============================================================================

class ConfirmDialog(ModalScreen[bool]):
    """A confirmation dialog."""
    
    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self.dialog_title = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Label(self.dialog_title, id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Confirm", variant="error", id="confirm")
    
    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)
    
    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(True)


# ============================================================================
# Main Application
# ============================================================================

class SysManage(App):
    """TUI System Management Application."""
    
    TITLE = "SysManage"
    CSS = CSS
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit", show=False),
        Binding("1", "show_system", "System", show=True),
        Binding("2", "show_nixos", "NixOS", show=True),
        Binding("3", "show_docker", "Docker", show=True),
        Binding("4", "show_logs", "Logs", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("c", "cancel_command", "Cancel", show=True),
    ]
    
    current_section = reactive("system")
    running_process: Optional[asyncio.subprocess.Process] = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Vertical(id="main-container"):
            # Top tabs bar
            with Horizontal(id="tabs-bar"):
                yield Button("💻 System", id="tab-system", classes="tab active")
                yield Button("❄️ NixOS", id="tab-nixos", classes="tab")
                yield Button("🐳 Docker", id="tab-docker", classes="tab")
                yield Button("📜 Logs", id="tab-logs", classes="tab")
            
            # Content area with sidebar and output
            with Horizontal(id="content-wrapper"):
                # Sidebar with commands
                with Vertical(id="sidebar"):
                    yield Label("Commands", id="sidebar-title")
                    
                    # System commands
                    with Vertical(id="sidebar-system", classes="sidebar-section visible"):
                        yield Button("Health Check", id="btn-health-run", classes="cmd-success")
                        yield Button("Quick Check", id="btn-health-quick", classes="cmd-info")
                        yield Button("System Info", id="btn-sys-refresh", classes="cmd-info")
                        yield Button("Disk Usage", id="btn-sys-disk", classes="cmd-info")
                        yield Button("Memory", id="btn-sys-memory", classes="cmd-info")
                        yield Button("Network", id="btn-sys-network", classes="cmd-info")
                        yield Button("Processes", id="btn-sys-processes", classes="cmd-info")
                        yield Label("─" * 18, classes="section-label")
                        yield Button("Reboot", id="btn-sys-reboot", classes="cmd-warning")
                        yield Button("Shutdown", id="btn-sys-shutdown", classes="cmd-danger")
                    
                    # NixOS commands
                    with Vertical(id="sidebar-nixos", classes="sidebar-section"):
                        yield Button("Switch", id="btn-nix-switch", classes="cmd-success")
                        yield Button("Test", id="btn-nix-test", classes="cmd-info")
                        yield Button("Build", id="btn-nix-build", classes="cmd-info")
                        yield Button("Boot", id="btn-nix-boot", classes="cmd-warning")
                        yield Label("─" * 18, classes="section-label")
                        yield Button("Update Flake", id="btn-nix-update", classes="cmd-info")
                        yield Button("Garbage Collect", id="btn-nix-gc", classes="cmd-warning")
                        yield Button("Optimise Store", id="btn-nix-optimise", classes="cmd-info")
                    
                    # Docker commands
                    with Vertical(id="sidebar-docker", classes="sidebar-section"):
                        yield Button("Refresh", id="btn-docker-refresh", classes="cmd-info")
                        yield Button("Prune System", id="btn-docker-prune", classes="cmd-warning")
                        yield Button("Prune+Volumes", id="btn-docker-prune-vol", classes="cmd-danger")
                        yield Label("─" * 18, classes="section-label")
                        yield Button("Start", id="btn-container-start", classes="cmd-success")
                        yield Button("Stop", id="btn-container-stop", classes="cmd-warning")
                        yield Button("Restart", id="btn-container-restart", classes="cmd-info")
                        yield Button("Logs", id="btn-container-logs", classes="cmd-info")
                        yield Button("Remove", id="btn-container-remove", classes="cmd-danger")
                    
                    # Logs commands
                    with Vertical(id="sidebar-logs", classes="sidebar-section"):
                        yield Button("System", id="btn-log-system", classes="cmd-info")
                        yield Button("Kernel", id="btn-log-kernel", classes="cmd-info")
                        yield Button("Docker", id="btn-log-docker", classes="cmd-info")
                        yield Button("Nginx", id="btn-log-nginx", classes="cmd-info")
                        yield Button("SSH", id="btn-log-sshd", classes="cmd-info")
                        yield Button("Tailscale", id="btn-log-tailscale", classes="cmd-info")
                        yield Button("Boot", id="btn-log-boot", classes="cmd-info")
                
                # Main output area
                with Vertical(id="output-area"):
                    # System output
                    with Vertical(id="output-system", classes="output-panel visible"):
                        yield RichLog(id="system-output", highlight=True, markup=True)
                    
                    # NixOS output
                    with Vertical(id="output-nixos", classes="output-panel"):
                        yield RichLog(id="nixos-output", highlight=True, markup=True)
                    
                    # Docker output
                    with Vertical(id="output-docker", classes="output-panel"):
                        yield OptionList(id="docker-containers")
                        yield RichLog(id="docker-output", highlight=True, markup=True)
                    
                    # Logs output
                    with Vertical(id="output-logs", classes="output-panel"):
                        yield RichLog(id="log-output", highlight=True, markup=True, max_lines=2000)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app."""
        self.title = f"SysManage - {HOSTNAME}"
        self.sub_title = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # ========================================================================
    # Section Navigation
    # ========================================================================
    
    def watch_current_section(self, section: str) -> None:
        """Update visible section when current_section changes."""
        # Update tab buttons
        for tab in self.query(".tab"):
            tab.remove_class("active")
        try:
            self.query_one(f"#tab-{section}").add_class("active")
        except Exception:
            pass
        
        # Update sidebar sections
        for sidebar in self.query(".sidebar-section"):
            sidebar.remove_class("visible")
        try:
            self.query_one(f"#sidebar-{section}").add_class("visible")
        except Exception:
            pass
        
        # Update output panels
        for panel in self.query(".output-panel"):
            panel.remove_class("visible")
        try:
            self.query_one(f"#output-{section}").add_class("visible")
        except Exception:
            pass
    
    @on(Button.Pressed, "#tab-system")
    def tab_system(self) -> None:
        self.current_section = "system"
    
    @on(Button.Pressed, "#tab-nixos")
    def tab_nixos(self) -> None:
        self.current_section = "nixos"
    
    @on(Button.Pressed, "#tab-docker")
    def tab_docker(self) -> None:
        self.current_section = "docker"
    
    @on(Button.Pressed, "#tab-logs")
    def tab_logs(self) -> None:
        self.current_section = "logs"
    
    def action_show_system(self) -> None:
        self.current_section = "system"
    
    def action_show_nixos(self) -> None:
        self.current_section = "nixos"
    
    def action_show_docker(self) -> None:
        self.current_section = "docker"
    
    def action_show_logs(self) -> None:
        self.current_section = "logs"
    
    def action_refresh(self) -> None:
        """Refresh current section."""
        if self.current_section == "system":
            self.run_health_check_to_system()
        elif self.current_section == "docker":
            self.refresh_docker()
    
    def action_cancel_command(self) -> None:
        """Cancel running command."""
        if self.running_process:
            try:
                self.running_process.terminate()
                self.notify("Command cancelled", severity="warning")
            except Exception:
                pass
    
    # ========================================================================
    # Command Execution
    # ========================================================================
    
    # ANSI to Rich markup conversion
    ANSI_TO_RICH = {
        '0': 'default',
        '1': 'bold',
        '0;31': 'red',
        '0;32': 'green',
        '0;33': 'yellow',
        '0;34': 'blue',
        '0;35': 'magenta',
        '0;36': 'cyan',
        '1;31': 'bold red',
        '1;32': 'bold green',
        '1;33': 'bold yellow',
        '1;34': 'bold blue',
        '31': 'red',
        '32': 'green',
        '33': 'yellow',
        '34': 'blue',
        '35': 'magenta',
        '36': 'cyan',
    }
    
    def convert_ansi_to_rich(self, text: str) -> Text:
        """Convert ANSI color codes to Rich Text object."""
        # Pattern to match ANSI escape sequences
        ansi_pattern = re.compile(r'\x1b\[([0-9;]*)m')
        
        result = Text()
        current_style = ""
        last_end = 0
        
        for match in ansi_pattern.finditer(text):
            # Add text before this match with current style
            if match.start() > last_end:
                segment = text[last_end:match.start()]
                if current_style:
                    result.append(segment, style=current_style)
                else:
                    result.append(segment)
            
            # Update style based on ANSI code
            code = match.group(1)
            if code == '0' or code == '':
                current_style = ""
            else:
                current_style = self.ANSI_TO_RICH.get(code, "")
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            segment = text[last_end:]
            if current_style:
                result.append(segment, style=current_style)
            else:
                result.append(segment)
        
        return result if result.plain else Text(text)
    
    @work(exclusive=True, thread=False)
    async def run_command(self, command: str, output_id: str, title: str = "") -> None:
        """Run a command and stream output to a RichLog widget."""
        log = self.query_one(f"#{output_id}", RichLog)
        log.clear()
        
        if title:
            log.write(Text(f"▶ {title}", style="bold cyan"))
            log.write(Text(f"$ {command}", style="dim"))
            log.write("")
        
        try:
            self.running_process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            
            while True:
                line = await self.running_process.stdout.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='replace').rstrip()
                
                # Check if line contains ANSI codes
                if '\x1b[' in text:
                    log.write(self.convert_ansi_to_rich(text))
                # Apply semantic coloring for lines without ANSI codes
                elif any(x in text.lower() for x in ['error', 'failed', 'failure', '✗']):
                    log.write(Text(text, style="red"))
                elif any(x in text.lower() for x in ['warning', 'warn', '⚠']):
                    log.write(Text(text, style="yellow"))
                elif any(x in text.lower() for x in ['success', '✓', 'done', 'ok ']):
                    log.write(Text(text, style="green"))
                elif text.startswith('===') or text.startswith('---') or text.startswith('╔') or text.startswith('║') or text.startswith('╚'):
                    log.write(Text(text, style="bold magenta"))
                else:
                    log.write(text)
            
            await self.running_process.wait()
            
            if self.running_process.returncode == 0:
                log.write("")
                log.write(Text("✓ Command completed successfully", style="bold green"))
            else:
                log.write("")
                log.write(Text(f"✗ Command exited with code {self.running_process.returncode}", style="bold red"))
        
        except asyncio.CancelledError:
            log.write(Text("\n⚠ Command cancelled", style="bold yellow"))
        except Exception as e:
            log.write(Text(f"\n✗ Error: {e}", style="bold red"))
        finally:
            self.running_process = None
    
    # ========================================================================
    # Health Check (in System section)
    # ========================================================================
    
    def run_health_check_to_system(self) -> None:
        """Run full health check to system output."""
        script_path = DOTFILES_PATH / "scripts" / "check-system-health.sh"
        if script_path.exists():
            self.run_command(f"bash {script_path}", "system-output", "System Health Check")
        else:
            self.run_quick_health_check_to_system()
    
    @on(Button.Pressed, "#btn-health-run")
    def run_health_check(self) -> None:
        """Run full health check."""
        self.run_health_check_to_system()
    
    def run_quick_health_check_to_system(self) -> None:
        """Run quick health check to system output."""
        commands = """
echo "=== Quick Health Check ==="
echo ""
echo "📍 Hostname: $(hostname)"
echo "🕐 Uptime: $(uptime -p)"
echo ""
echo "=== Services ==="
systemctl is-active --quiet docker && echo "✓ Docker: Running" || echo "✗ Docker: Not running"
systemctl is-active --quiet sshd && echo "✓ SSH: Running" || echo "✗ SSH: Not running"
systemctl is-active --quiet tailscaled && echo "✓ Tailscale: Running" || echo "✗ Tailscale: Not running"
systemctl is-active --quiet NetworkManager && echo "✓ NetworkManager: Running" || echo "✗ NetworkManager: Not running"
echo ""
echo "=== Disk Space ==="
df -h / /home /nix 2>/dev/null | tail -n +2
echo ""
echo "=== Memory ==="
free -h | head -2
echo ""
echo "=== Failed Services ==="
systemctl list-units --state=failed --no-legend | head -5 || echo "None"
"""
        self.run_command(commands, "system-output", "Quick Health Check")
    
    @on(Button.Pressed, "#btn-health-quick")
    def run_quick_health_check(self) -> None:
        """Run quick health check."""
        self.run_quick_health_check_to_system()
    
    # ========================================================================
    # NixOS Management
    # ========================================================================
    
    @on(Button.Pressed, "#btn-nix-switch")
    def nix_switch(self) -> None:
        self.run_command(NIXOS_COMMANDS["switch"], "nixos-output", "NixOS Rebuild Switch")
    
    @on(Button.Pressed, "#btn-nix-test")
    def nix_test(self) -> None:
        self.run_command(NIXOS_COMMANDS["test"], "nixos-output", "NixOS Rebuild Test")
    
    @on(Button.Pressed, "#btn-nix-build")
    def nix_build(self) -> None:
        self.run_command(NIXOS_COMMANDS["build"], "nixos-output", "NixOS Rebuild Build")
    
    @on(Button.Pressed, "#btn-nix-boot")
    def nix_boot(self) -> None:
        self.run_command(NIXOS_COMMANDS["boot"], "nixos-output", "NixOS Rebuild Boot")
    
    @on(Button.Pressed, "#btn-nix-update")
    def nix_update(self) -> None:
        self.run_command(NIXOS_COMMANDS["update"], "nixos-output", "Update Flake Inputs")
    
    @on(Button.Pressed, "#btn-nix-gc")
    @work
    async def nix_gc(self) -> None:
        if await self.push_screen_wait(
            ConfirmDialog("Garbage Collection", "Delete old generations and unused store paths?")
        ):
            self.run_command(NIXOS_COMMANDS["gc"], "nixos-output", "Garbage Collection")
    
    @on(Button.Pressed, "#btn-nix-optimise")
    def nix_optimise(self) -> None:
        self.run_command(NIXOS_COMMANDS["optimise"], "nixos-output", "Optimise Nix Store")
    
    # ========================================================================
    # Docker Management
    # ========================================================================
    
    @work(thread=True)
    def refresh_docker(self) -> None:
        """Refresh docker containers list."""
        try:
            # Get containers
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"],
                capture_output=True, text=True, timeout=10
            )
            
            # Update option list
            def update_ui():
                option_list = self.query_one("#docker-containers", OptionList)
                option_list.clear_options()
                
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split('|')
                        if len(parts) >= 3:
                            name, status, image = parts[0], parts[1], parts[2]
                            # Color based on status
                            if 'Up' in status:
                                status_icon = "🟢"
                            elif 'Exited' in status:
                                status_icon = "🔴"
                            else:
                                status_icon = "🟡"
                            option_list.add_option(Option(f"{status_icon} {name} ({image[:30]})", id=name))
                else:
                    option_list.add_option(Option("No containers found"))
            
            self.call_from_thread(update_ui)
            
            # Also show full info in output
            self.call_from_thread(
                lambda: self.run_command(DOCKER_COMMANDS["ps"], "docker-output", "Docker Containers")
            )
        except Exception as e:
            self.call_from_thread(lambda: self.notify(f"Error: {e}", severity="error"))
    
    @on(Button.Pressed, "#btn-docker-refresh")
    def docker_refresh(self) -> None:
        self.refresh_docker()
    
    @on(Button.Pressed, "#btn-docker-prune")
    @work
    async def docker_prune(self) -> None:
        if await self.push_screen_wait(
            ConfirmDialog("Docker Prune", "Remove all unused containers, networks, and images?")
        ):
            self.run_command(DOCKER_COMMANDS["prune"], "docker-output", "Docker System Prune")
    
    @on(Button.Pressed, "#btn-docker-prune-vol")
    @work
    async def docker_prune_volumes(self) -> None:
        if await self.push_screen_wait(
            ConfirmDialog("Docker Prune + Volumes", "⚠️ This will also delete ALL volumes! Are you sure?")
        ):
            self.run_command(DOCKER_COMMANDS["prune_volumes"], "docker-output", "Docker System Prune (with volumes)")
    
    def get_selected_container(self) -> Optional[str]:
        """Get currently selected container name."""
        option_list = self.query_one("#docker-containers", OptionList)
        if option_list.highlighted is not None:
            option = option_list.get_option_at_index(option_list.highlighted)
            if option and option.id:
                return str(option.id)
        return None
    
    @on(Button.Pressed, "#btn-container-start")
    def container_start(self) -> None:
        container = self.get_selected_container()
        if container:
            self.run_command(f"docker start {container}", "docker-output", f"Starting {container}")
    
    @on(Button.Pressed, "#btn-container-stop")
    def container_stop(self) -> None:
        container = self.get_selected_container()
        if container:
            self.run_command(f"docker stop {container}", "docker-output", f"Stopping {container}")
    
    @on(Button.Pressed, "#btn-container-restart")
    def container_restart(self) -> None:
        container = self.get_selected_container()
        if container:
            self.run_command(f"docker restart {container}", "docker-output", f"Restarting {container}")
    
    @on(Button.Pressed, "#btn-container-logs")
    def container_logs(self) -> None:
        container = self.get_selected_container()
        if container:
            self.run_command(f"docker logs -f --tail 100 {container}", "docker-output", f"Logs: {container}")
    
    @on(Button.Pressed, "#btn-container-remove")
    @work
    async def container_remove(self) -> None:
        container = self.get_selected_container()
        if container:
            if await self.push_screen_wait(
                ConfirmDialog("Remove Container", f"Remove container '{container}'?")
            ):
                self.run_command(f"docker rm -f {container}", "docker-output", f"Removing {container}")
    
    # ========================================================================
    # Log Viewer
    # ========================================================================
    
    @on(Button.Pressed, "#btn-log-system")
    def log_system(self) -> None:
        self.run_command(LOG_COMMANDS["system"], "log-output", "System Logs")
    
    @on(Button.Pressed, "#btn-log-kernel")
    def log_kernel(self) -> None:
        self.run_command(LOG_COMMANDS["kernel"], "log-output", "Kernel Logs")
    
    @on(Button.Pressed, "#btn-log-docker")
    def log_docker(self) -> None:
        self.run_command(LOG_COMMANDS["docker"], "log-output", "Docker Logs")
    
    @on(Button.Pressed, "#btn-log-nginx")
    def log_nginx(self) -> None:
        self.run_command(LOG_COMMANDS["nginx"], "log-output", "Nginx Logs")
    
    @on(Button.Pressed, "#btn-log-sshd")
    def log_sshd(self) -> None:
        self.run_command(LOG_COMMANDS["sshd"], "log-output", "SSH Logs")
    
    @on(Button.Pressed, "#btn-log-tailscale")
    def log_tailscale(self) -> None:
        self.run_command(LOG_COMMANDS["tailscale"], "log-output", "Tailscale Logs")
    
    @on(Button.Pressed, "#btn-log-boot")
    def log_boot(self) -> None:
        self.run_command(LOG_COMMANDS["boot"], "log-output", "Boot Logs")
    
    # ========================================================================
    # System Info
    # ========================================================================
    
    @on(Button.Pressed, "#btn-sys-refresh")
    def refresh_system_info(self) -> None:
        """Show comprehensive system info."""
        commands = f"""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               SYSTEM INFORMATION                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🖥️  Hostname: $(hostname)"
echo "🐧 Kernel: $(uname -r)"
echo "⏱️  Uptime: $(uptime -p)"
echo "📅 Date: $(date)"
echo ""
echo "═══════════════════════ CPU ═══════════════════════"
lscpu | grep -E "Model name|CPU\\(s\\)|Thread|Core|MHz" | head -5
echo ""
echo "═══════════════════════ MEMORY ═══════════════════════"
free -h
echo ""
echo "═══════════════════════ DISK ═══════════════════════"
df -h | grep -E "^/dev|Filesystem"
echo ""
echo "═══════════════════════ NIXOS ═══════════════════════"
nixos-version 2>/dev/null || echo "Not a NixOS system"
echo "Flake: {DOTFILES_PATH}"
echo ""
echo "═══════════════════════ NETWORK ═══════════════════════"
ip -brief addr | grep -v "^lo"
"""
        self.run_command(commands, "system-output", "System Information")
    
    @on(Button.Pressed, "#btn-sys-disk")
    def sys_disk(self) -> None:
        commands = """
echo "═══════════════════════ DISK USAGE ═══════════════════════"
echo ""
df -h
echo ""
echo "═══════════════════════ LARGEST DIRECTORIES ═══════════════════════"
echo ""
du -sh /nix/store 2>/dev/null || true
du -sh /home/* 2>/dev/null | sort -rh | head -10
echo ""
echo "═══════════════════════ NIX STORE ═══════════════════════"
nix-store --gc --print-dead 2>/dev/null | wc -l | xargs echo "Dead paths:"
"""
        self.run_command(commands, "system-output", "Disk Usage")
    
    @on(Button.Pressed, "#btn-sys-memory")
    def sys_memory(self) -> None:
        commands = """
echo "═══════════════════════ MEMORY USAGE ═══════════════════════"
echo ""
free -h
echo ""
echo "═══════════════════════ TOP MEMORY CONSUMERS ═══════════════════════"
echo ""
ps aux --sort=-%mem | head -15
"""
        self.run_command(commands, "system-output", "Memory Usage")
    
    @on(Button.Pressed, "#btn-sys-network")
    def sys_network(self) -> None:
        commands = """
echo "═══════════════════════ NETWORK INTERFACES ═══════════════════════"
echo ""
ip -brief addr
echo ""
echo "═══════════════════════ ROUTING TABLE ═══════════════════════"
echo ""
ip route
echo ""
echo "═══════════════════════ TAILSCALE STATUS ═══════════════════════"
echo ""
tailscale status 2>/dev/null || echo "Tailscale not available"
echo ""
echo "═══════════════════════ LISTENING PORTS ═══════════════════════"
echo ""
ss -tlnp 2>/dev/null | head -20
"""
        self.run_command(commands, "system-output", "Network Info")
    
    @on(Button.Pressed, "#btn-sys-processes")
    def sys_processes(self) -> None:
        commands = """
echo "═══════════════════════ TOP PROCESSES (CPU) ═══════════════════════"
echo ""
ps aux --sort=-%cpu | head -15
echo ""
echo "═══════════════════════ SYSTEMD SERVICES ═══════════════════════"
echo ""
systemctl list-units --type=service --state=running | head -20
"""
        self.run_command(commands, "system-output", "Processes")
    
    @on(Button.Pressed, "#btn-sys-reboot")
    @work
    async def sys_reboot(self) -> None:
        if await self.push_screen_wait(
            ConfirmDialog("Reboot System", "⚠️ Are you sure you want to reboot?")
        ):
            self.run_command("sudo systemctl reboot", "system-output", "Rebooting...")
    
    @on(Button.Pressed, "#btn-sys-shutdown")
    @work
    async def sys_shutdown(self) -> None:
        if await self.push_screen_wait(
            ConfirmDialog("Shutdown System", "⚠️ Are you sure you want to shut down?")
        ):
            self.run_command("sudo systemctl poweroff", "system-output", "Shutting down...")


# ============================================================================
# Entry Point
# ============================================================================

def main():
    app = SysManage()
    app.run()


if __name__ == "__main__":
    main()

