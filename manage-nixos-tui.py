#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.rich python3Packages.textual
"""
NixOS Configuration Manager - Full TUI
A beautiful terminal user interface for managing NixOS configurations across multiple machines.
"""

import subprocess
import sys
import os
import shutil
import threading
import textwrap
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header, Footer, Static, ListView, ListItem, Label, 
        Button, DataTable, Log, Tabs, Tab, TextArea, Collapsible
    )
    from textual.containers import Container, Horizontal, Vertical, Grid
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
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box
except ImportError:
    print("Error: rich library not found. Please install it with:")
    print("  pip install rich")
    print("  or")
    print("  nix-shell -p python3Packages.rich")
    sys.exit(1)


class ActionList(Static):
    """Widget for displaying and selecting actions."""
    
    class ActionSelected(Message):
        """Message sent when an action is selected."""
        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()
    
    ACTIONS = [
        ("switch", "Switch Configuration", "Apply configuration immediately"),
        ("boot", "Boot Configuration", "Apply on next boot"),
        ("build", "Build Configuration", "Build only, don't apply"),
        ("dry-run", "Dry Run", "Test configuration changes"),
        ("update", "Update Flake Inputs", "Update all dependencies"),
        ("update-nixpkgs", "Update Nixpkgs", "Update nixpkgs input only"),
        ("rebuild-all", "Rebuild All", "Build all machine configurations"),
        ("status", "System Status", "Show generations and status"),
        ("health", "Health Check", "Run system diagnostics"),
        ("gc", "Garbage Collection", "Clean up old generations"),
        ("pull", "Git Pull", "Pull latest changes"),
        ("list", "List Machines", "Show all available machines"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]Actions[/bold cyan]", classes="section-title")
        for idx, (action_id, title, desc) in enumerate(self.ACTIONS):
            prefix = "❯ " if idx == self.selected_index else "  "
            yield Static(f"{prefix}[bold]{title}[/bold]\n[dim]{desc}[/dim]", 
                       classes="action-item", id=f"action-{idx}")
    
    def on_mount(self) -> None:
        self._highlight_selected()
    
    def _highlight_selected(self) -> None:
        for idx, (action_id, title, desc) in enumerate(self.ACTIONS):
            item = self.query_one(f"#action-{idx}", Static)
            if idx == self.selected_index:
                item.styles.bg = "cyan"
                item.styles.color = "white"
                item.update(f"❯ [bold]{title}[/bold]\n[dim]{desc}[/dim]")
            else:
                item.styles.bg = "transparent"
                item.styles.color = "white"
                item.update(f"  {title}\n[dim]{desc}[/dim]")
    
    def select_next(self) -> None:
        if self.selected_index < len(self.ACTIONS) - 1:
            self.selected_index += 1
            self._highlight_selected()
    
    def select_previous(self) -> None:
        self.selected_index = max(0, self.selected_index - 1)
        self._highlight_selected()
    
    def get_selected(self) -> Tuple[str, str]:
        action_id, title, desc = self.ACTIONS[self.selected_index]
        return action_id, title


class OutputLog(Log):
    """Widget for displaying command output."""
    pass


class NixOSManagerApp(App):
    """Main TUI application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .section-title {
        text-style: bold;
        margin: 1;
        height: 3;
    }
    
    .machine-item {
        padding: 1;
        margin: 0 1;
        height: 3;
    }
    
    .action-item {
        padding: 1;
        margin: 0 1;
        height: 4;
    }
    
    #action-panel {
        width: 30%;
        border: solid $primary;
        padding: 1;
    }
    
    #output-panel {
        width: 70%;
        border: solid $primary;
        padding: 1;
    }
    
    #status-bar {
        dock: bottom;
        height: 3;
        background: $panel;
    }
    
    .info-text {
        text-align: center;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("up", "navigate_up", "Up", priority=True),
        Binding("down", "navigate_down", "Down", priority=True),
        Binding("enter", "execute_action", "Execute", priority=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.flake_path = Path(__file__).parent.absolute()
        self.machines_list = ["brian-laptop", "superheavy", "docker", "backup"]
        self.current_machine = self._detect_current_machine()
    
    def _detect_current_machine(self) -> Optional[str]:
        """Detect the current machine from hostname."""
        try:
            hostname = subprocess.check_output(["hostname"], text=True).strip()
            if hostname in self.machines_list:
                return hostname
        except Exception:
            pass
        return None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        
        with Horizontal():
            with Container(id="action-panel"):
                yield ActionList(id="action-list")
            
            with Container(id="output-panel"):
                yield Static("[bold cyan]Output[/bold cyan]", classes="section-title")
                yield OutputLog(id="output-log")
        
        with Container(id="status-bar"):
            current_info = f"Current Machine: [bold green]{self.current_machine}[/bold green]" if self.current_machine else "[yellow]Machine not detected[/yellow]"
            yield Static(f"{current_info} | [dim]Use arrow keys to navigate, Enter to execute, q to quit[/dim]", 
                        classes="info-text")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app starts."""
        self.set_focus(self.query_one("#action-list"))
    
    def action_navigate_up(self) -> None:
        """Navigate up in the actions panel."""
        self.query_one("#action-list", ActionList).select_previous()
    
    def action_navigate_down(self) -> None:
        """Navigate down in the actions panel."""
        self.query_one("#action-list", ActionList).select_next()
    
    def action_execute_action(self) -> None:
        """Execute the selected action."""
        action_list = self.query_one("#action-list", ActionList)
        action_id, title = action_list.get_selected()
        
        # Use current machine for actions that need it
        machine = self.current_machine if action_id in ["switch", "boot", "build", "dry-run", "status"] else None
        
        # Execute the action
        self.execute_command(action_id, machine, title)
    
    def execute_command(self, action_id: str, machine: Optional[str], title: str) -> None:
        """Execute a command and display output."""
        output_log = self.query_one("#output-log", OutputLog)
        output_log.clear()
        output_log.write(f"[bold cyan]Executing: {title}[/bold cyan]")
        
        # Check if machine is needed but not detected
        if action_id in ["switch", "boot", "build", "dry-run", "status"]:
            if not machine:
                output_log.write(f"\n[bold red]Error: Machine not detected![/bold red]\n")
                output_log.write(f"[yellow]Could not detect current machine from hostname.[/yellow]\n")
                output_log.write(f"[yellow]Available machines: {', '.join(self.machines_list)}[/yellow]\n")
                output_log.write(f"[dim]Please ensure you're running this on a configured machine.[/dim]\n")
                return
            output_log.write(f"[dim]Machine: {machine}[/dim]\n")
        
        try:
            if action_id == "switch":
                self._cmd_switch(machine, output_log)
            elif action_id == "boot":
                self._cmd_boot(machine, output_log)
            elif action_id == "build":
                self._cmd_build(machine, output_log)
            elif action_id == "dry-run":
                self._cmd_dry_run(machine, output_log)
            elif action_id == "update":
                self._cmd_update(output_log)
            elif action_id == "update-nixpkgs":
                self._cmd_update_nixpkgs(output_log)
            elif action_id == "rebuild-all":
                self._cmd_rebuild_all(output_log)
            elif action_id == "status":
                self._cmd_status(machine, output_log)
            elif action_id == "health":
                self._cmd_health(output_log)
            elif action_id == "gc":
                self._cmd_gc(output_log)
            elif action_id == "pull":
                self._cmd_pull(output_log)
            elif action_id == "list":
                self._cmd_list_machines(output_log)
        except Exception as e:
            output_log.write(f"[bold red]Error: {e}[/bold red]")
            import traceback
            output_log.write(f"[red]{traceback.format_exc()}[/red]")
    
    def _run_command(self, cmd: List[str], sudo: bool = False, 
                     capture_output: bool = True) -> Tuple[int, str]:
        """Run a command and return exit code and output."""
        if sudo:
            cmd = ["sudo"] + cmd
        
        try:
            result = subprocess.run(
                cmd, cwd=self.flake_path, capture_output=True, text=True, check=False
            )
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            return 1, str(e)
    
    def _run_command_streaming(self, cmd: List[str], output_log: OutputLog, 
                               sudo: bool = False) -> int:
        """Run a command and stream output live to the output log."""
        if sudo:
            cmd = ["sudo"] + cmd
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.flake_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Read and write output line by line in a thread-safe way
            def read_output():
                try:
                    # Use a reasonable width for wrapping (accounting for panel width ~70% of screen)
                    # Assuming typical terminal width, 70% would be around 80-100 chars
                    wrap_width = 100
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            line = line.rstrip()
                            # Wrap long lines to prevent horizontal scrolling
                            if len(line) > wrap_width:
                                wrapped_lines = textwrap.wrap(line, width=wrap_width, break_long_words=True, break_on_hyphens=False)
                                for wrapped_line in wrapped_lines:
                                    self.call_from_thread(output_log.write, wrapped_line)
                            else:
                                # Use call_from_thread to safely update UI from background thread
                                self.call_from_thread(output_log.write, line)
                except Exception:
                    pass
            
            # Start reading in a background thread
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            
            # Wait for process to complete
            process.wait()
            reader_thread.join(timeout=0.1)  # Brief wait for any remaining output
            
            return process.returncode
        except Exception as e:
            self.call_from_thread(output_log.write, f"[bold red]Error: {e}[/bold red]\n")
            return 1
    
    def _cmd_switch(self, machine: str, output_log: OutputLog) -> None:
        """Switch to a machine configuration."""
        output_log.write(f"[bold]Switching to {machine} configuration...[/bold]\n\n")
        cmd = ["nixos-rebuild", "switch", "--flake", f".#{machine}"]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=True)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write(f"[bold green]✓ Successfully switched to {machine} configuration![/bold green]\n")
        else:
            output_log.write(f"[bold red]✗ Failed to switch configuration[/bold red]\n")
    
    def _cmd_boot(self, machine: str, output_log: OutputLog) -> None:
        """Build configuration for next boot."""
        output_log.write(f"[bold]Building {machine} configuration for next boot...[/bold]\n\n")
        cmd = ["nixos-rebuild", "boot", "--flake", f".#{machine}"]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=True)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write(f"[bold green]✓ Configuration will be applied on next boot![/bold green]\n")
        else:
            output_log.write(f"[bold red]✗ Failed to build configuration[/bold red]\n")
    
    def _cmd_build(self, machine: str, output_log: OutputLog) -> None:
        """Build configuration without applying."""
        output_log.write(f"[bold]Building {machine} configuration...[/bold]\n\n")
        cmd = [
            "nix", "build",
            f".#nixosConfigurations.{machine}.config.system.build.toplevel",
            "--extra-experimental-features", "nix-command",
            "--extra-experimental-features", "flakes",
            "-o", "result"
        ]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=False)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write(f"[bold green]✓ Successfully built {machine} configuration![/bold green]\n")
        else:
            output_log.write(f"[bold red]✗ Failed to build configuration[/bold red]\n")
    
    def _cmd_dry_run(self, machine: str, output_log: OutputLog) -> None:
        """Perform a dry run."""
        output_log.write(f"[bold]Performing dry run for {machine}...[/bold]\n\n")
        cmd = ["nixos-rebuild", "dry-run", "--flake", f".#{machine}"]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=True)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write(f"[bold green]✓ Dry run completed successfully![/bold green]\n")
        else:
            output_log.write(f"[bold red]✗ Dry run failed[/bold red]\n")
    
    def _cmd_update(self, output_log: OutputLog) -> None:
        """Update all flake inputs."""
        output_log.write("[bold]Updating all flake inputs...[/bold]\n\n")
        cmd = [
            "nix", "flake", "update",
            "--extra-experimental-features", "nix-command",
            "--extra-experimental-features", "flakes"
        ]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=False)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write("[bold green]✓ Flake inputs updated successfully![/bold green]\n")
        else:
            output_log.write("[bold red]✗ Failed to update flake inputs[/bold red]\n")
    
    def _cmd_update_nixpkgs(self, output_log: OutputLog) -> None:
        """Update nixpkgs only."""
        output_log.write("[bold]Updating nixpkgs...[/bold]\n\n")
        cmd = [
            "nix", "flake", "update", "nixpkgs",
            "--extra-experimental-features", "nix-command",
            "--extra-experimental-features", "flakes"
        ]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=False)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write("[bold green]✓ Nixpkgs updated successfully![/bold green]\n")
        else:
            output_log.write("[bold red]✗ Failed to update nixpkgs[/bold red]\n")
    
    def _cmd_rebuild_all(self, output_log: OutputLog) -> None:
        """Rebuild all machine configurations."""
        output_log.write("[bold]Building all machine configurations...[/bold]\n\n")
        failed_machines = []
        
        for machine in self.machines_list:
            output_log.write(f"[bold]Building {machine}...[/bold]\n\n")
            cmd = [
                "nix", "build",
                f".#nixosConfigurations.{machine}.config.system.build.toplevel",
                "--extra-experimental-features", "nix-command",
                "--extra-experimental-features", "flakes"
            ]
            exit_code = self._run_command_streaming(cmd, output_log, sudo=False)
            output_log.write("\n")
            if exit_code == 0:
                output_log.write(f"[bold green]✓ {machine} built successfully[/bold green]\n")
            else:
                output_log.write(f"[bold red]✗ Failed to build {machine}[/bold red]\n")
                failed_machines.append(machine)
            output_log.write("\n")
        
        if not failed_machines:
            output_log.write("[bold green]✓ All machines built successfully![/bold green]\n")
        else:
            output_log.write("[bold red]✗ Failed to build the following machines:[/bold red]\n")
            for machine in failed_machines:
                output_log.write(f"  [red]- {machine}[/red]\n")
    
    def _cmd_status(self, machine: str, output_log: OutputLog) -> None:
        """Show system status."""
        output_log.write(f"[bold]System Status for {machine}[/bold]\n\n")
        
        if os.path.exists("/etc/nixos/configuration.nix"):
            if shutil.which("nixos-rebuild"):
                output_log.write("[bold]Available Generations:[/bold]\n\n")
                cmd = ["nixos-rebuild", "list-generations"]
                exit_code = self._run_command_streaming(cmd, output_log, sudo=False)
                if exit_code != 0:
                    output_log.write("[yellow]Unable to retrieve generations[/yellow]\n")
            else:
                output_log.write("[yellow]nixos-rebuild not available[/yellow]\n")
        else:
            output_log.write("[yellow]This machine doesn't appear to be the current system[/yellow]\n")
    
    def _cmd_health(self, output_log: OutputLog) -> None:
        """Run system health check."""
        health_script = self.flake_path / "scripts" / "check-system-health.sh"
        
        if not health_script.exists():
            output_log.write(f"[red]Error: Health check script not found at {health_script}[/red]\n")
            return
        
        if not os.access(health_script, os.X_OK):
            os.chmod(health_script, 0o755)
        
        output_log.write("[bold]Running system health check...[/bold]\n\n")
        exit_code = self._run_command_streaming([str(health_script)], output_log, sudo=False)
    
    def _cmd_gc(self, output_log: OutputLog) -> None:
        """Run garbage collection."""
        output_log.write("[bold]Running garbage collection...[/bold]\n\n")
        cmd = ["nix-collect-garbage", "-d"]
        exit_code = self._run_command_streaming(cmd, output_log, sudo=True)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write("[bold green]✓ Garbage collection complete![/bold green]\n")
            output_log.write("[dim]Note: Old system generations (>7 days) are automatically cleaned up weekly[/dim]\n")
        else:
            output_log.write("[bold red]✗ Garbage collection failed[/bold red]\n")
    
    def _cmd_pull(self, output_log: OutputLog) -> None:
        """Git pull and rerun."""
        output_log.write("[bold]Pulling latest changes from git...[/bold]\n\n")
        exit_code = self._run_command_streaming(["git", "pull"], output_log, sudo=False)
        output_log.write("\n")
        if exit_code == 0:
            output_log.write("[bold green]✓ Git pull completed successfully![/bold green]\n")
            output_log.write("[yellow]Please restart the TUI to use the latest changes.[/yellow]\n")
        else:
            output_log.write("[bold red]✗ Git pull failed[/bold red]\n")
    
    def _cmd_list_machines(self, output_log: OutputLog) -> None:
        """List all available machines."""
        output_log.write("[bold]Available Machines[/bold]\n\n")
        for machine_name in self.machines_list:
            status = "[bold green](Current)[/bold green]" if machine_name == self.current_machine else "[dim](Available)[/dim]"
            output_log.write(f"  {machine_name} {status}\n")


def main():
    """Main entry point."""
    app = NixOSManagerApp()
    app.run()


if __name__ == "__main__":
    main()
