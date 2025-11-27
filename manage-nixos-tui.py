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
import pty
import select
import fcntl
import time
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


class ActionItem(Static):
    """A clickable action item."""
    
    def __init__(self, action_id: str, title: str, desc: str, index: int, **kwargs):
        super().__init__(**kwargs)
        self.action_id = action_id
        self.title = title
        self.desc = desc
        self.index = index
    
    def on_click(self, event: events.Click) -> None:
        """Handle click on this action item."""
        # Send message to parent ActionList
        self.post_message(ActionList.ActionSelected(self.action_id))


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
            yield ActionItem(
                action_id, title, desc, idx,
                content=f"{prefix}[bold]{title}[/bold]",
                classes="action-item", 
                id=f"action-{idx}"
            )
        
        # Add descriptions section
        yield Static("[bold cyan]Descriptions[/bold cyan]", classes="section-title")
        descriptions_text = "\n".join([f"[bold]{title}:[/bold] {desc}" 
                                      for _, title, desc in self.ACTIONS])
        yield Static(descriptions_text, classes="descriptions")
    
    def on_mount(self) -> None:
        self._highlight_selected()
    
    def _highlight_selected(self) -> None:
        for idx, (action_id, title, desc) in enumerate(self.ACTIONS):
            item = self.query_one(f"#action-{idx}", ActionItem)
            if idx == self.selected_index:
                item.styles.bg = "cyan"
                item.styles.color = "white"
                item.update(f"❯ [bold]{title}[/bold]")
            else:
                item.styles.bg = "transparent"
                item.styles.color = "white"
                item.update(f"  {title}")
    
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
    
    @on(ActionSelected)
    def on_action_selected(self, event: ActionSelected) -> None:
        """Handle action selection from click or keyboard."""
        # Find the index of the selected action
        for idx, (action_id, _, _) in enumerate(self.ACTIONS):
            if action_id == event.action:
                self.selected_index = idx
                self._highlight_selected()
                break


class OutputLog(Log):
    """Widget for displaying command output."""
    
    class OutputUpdate(Message):
        """Message to update output from background thread."""
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()
    
    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup tags from text."""
        import re
        # Remove Rich markup tags like [bold], [cyan], [/bold], etc.
        return re.sub(r'\[/?[^\]]+\]', '', text)
    
    @on(OutputUpdate)
    def on_output_update(self, event: OutputUpdate) -> None:
        """Handle output update message."""
        # Strip markup since Textual's Log doesn't render it properly
        plain_text = self._strip_markup(event.text)
        self.write(plain_text)
        # Force immediate refresh and scroll to bottom
        self.refresh()
        self.scroll_end(animate=False)
    
    def write(self, content) -> None:
        """Override write to strip Rich markup."""
        if isinstance(content, str):
            content = self._strip_markup(content)
        super().write(content)


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
        height: 3;
    }
    
    .action-item:hover {
        background: $primary 20%;
    }
    
    .descriptions {
        padding: 1;
        margin: 1;
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
    
    @on(ActionList.ActionSelected)
    def on_action_selected(self, event: ActionList.ActionSelected) -> None:
        """Handle action selection from mouse click."""
        action_id = event.action
        # Find the action title
        action_list = self.query_one("#action-list", ActionList)
        for action_tuple in ActionList.ACTIONS:
            if action_tuple[0] == action_id:
                title = action_tuple[1]
                # Use current machine for actions that need it
                machine = self.current_machine if action_id in ["switch", "boot", "build", "dry-run", "status"] else None
                # Execute the action
                self.execute_command(action_id, machine, title)
                break
    
    def execute_command(self, action_id: str, machine: Optional[str], title: str) -> None:
        """Execute a command and display output."""
        output_log = self.query_one("#output-log", OutputLog)
        output_log.clear()
        output_log.write(f"[bold cyan]Executing: {title}[/bold cyan]\n")
        
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
        """Run a command and stream output live to the output log using pty for unbuffered output."""
        # Try to use 'script' command which creates a proper terminal session
        # This works better than pty for some commands that buffer heavily
        use_script = False
        try:
            subprocess.run(["which", "script"], capture_output=True, check=True)
            use_script = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Set environment
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        if use_script:
            # Use 'script' to create a terminal session - this forces unbuffered output
            # script -qefc runs command in a terminal and outputs to stdout
            script_cmd = " ".join(cmd)
            if sudo:
                full_cmd = ["sudo", "script", "-qefc", script_cmd, "/dev/null"]
            else:
                full_cmd = ["script", "-qefc", script_cmd, "/dev/null"]
            cmd = full_cmd
            use_pty = False  # script creates its own terminal
        else:
            # Try stdbuf as fallback
            try:
                subprocess.run(["which", "stdbuf"], capture_output=True, check=True)
                if sudo:
                    cmd = ["sudo", "stdbuf", "-oL", "-eL"] + cmd
                else:
                    cmd = ["stdbuf", "-oL", "-eL"] + cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                if sudo:
                    cmd = ["sudo"] + cmd
            use_pty = True
        
        try:
            if use_pty:
                # Use pty to create a pseudo-terminal
                master_fd, slave_fd = pty.openpty()
                
                # Start the process with pty
                process = subprocess.Popen(
                    cmd,
                    cwd=self.flake_path,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True
                )
                os.close(slave_fd)
                read_fd = master_fd
            else:
                # Use script - read from stdout directly
                process = subprocess.Popen(
                    cmd,
                    cwd=self.flake_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True,
                    bufsize=0  # Unbuffered
                )
                read_fd = process.stdout.fileno()
                master_fd = None
            
            # Read and write output in real-time
            def read_output():
                try:
                    wrap_width = 70
                    line_buffer = ""
                    
                    # Set read fd to non-blocking
                    if use_pty:
                        flags = fcntl.fcntl(read_fd, fcntl.F_GETFL)
                        fcntl.fcntl(read_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    else:
                        # For regular pipe, set to non-blocking
                        flags = fcntl.fcntl(read_fd, fcntl.F_GETFL)
                        fcntl.fcntl(read_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    
                    while True:
                        try:
                            # Read available data (non-blocking)
                            chunk = os.read(read_fd, 512)
                            if not chunk:
                                # Check if process is done
                                if process.poll() is not None:
                                    # Write any remaining buffer
                                    if line_buffer:
                                        line = line_buffer.rstrip('\r\n')
                                        if line:
                                            if len(line) > wrap_width:
                                                wrapped_lines = textwrap.wrap(line, width=wrap_width, break_long_words=True, break_on_hyphens=False, replace_whitespace=False)
                                                for wrapped_line in wrapped_lines:
                                                    self.call_from_thread(output_log.write, wrapped_line + "\n")
                                                self.call_from_thread(output_log.refresh)
                                                self.call_from_thread(output_log.scroll_end, animate=False)
                                            else:
                                                self.call_from_thread(output_log.write, line + "\n")
                                                self.call_from_thread(output_log.refresh)
                                                self.call_from_thread(output_log.scroll_end, animate=False)
                                    break
                                # No data available, small sleep to avoid busy waiting
                                time.sleep(0.01)
                                continue
                            
                            # Decode chunk and process
                            text = chunk.decode('utf-8', errors='replace')
                            line_buffer += text
                            
                            # Process complete lines immediately
                            while '\n' in line_buffer:
                                line, line_buffer = line_buffer.split('\n', 1)
                                line = line.rstrip('\r')
                                if line:
                                    # Wrap long lines and write immediately
                                    if len(line) > wrap_width:
                                        wrapped_lines = textwrap.wrap(line, width=wrap_width, break_long_words=True, break_on_hyphens=False, replace_whitespace=False)
                                        for wrapped_line in wrapped_lines:
                                            self.call_from_thread(output_log.write, wrapped_line + "\n")
                                        # Refresh once after all wrapped lines
                                        self.call_from_thread(output_log.refresh)
                                        self.call_from_thread(output_log.scroll_end, animate=False)
                                    else:
                                        self.call_from_thread(output_log.write, line + "\n")
                                        self.call_from_thread(output_log.refresh)
                                        self.call_from_thread(output_log.scroll_end, animate=False)
                        except BlockingIOError:
                            # No data available right now
                            if process.poll() is not None:
                                # Process done, check for final output
                                try:
                                    final_chunk = os.read(read_fd, 4096)
                                    if final_chunk:
                                        text = final_chunk.decode('utf-8', errors='replace')
                                        line_buffer += text
                                        if '\n' in line_buffer:
                                            line, line_buffer = line_buffer.split('\n', 1)
                                            line = line.rstrip('\r')
                                            if line:
                                                if len(line) > wrap_width:
                                                    wrapped_lines = textwrap.wrap(line, width=wrap_width, break_long_words=True, break_on_hyphens=False, replace_whitespace=False)
                                                    for wrapped_line in wrapped_lines:
                                                        self.call_from_thread(output_log.write, wrapped_line + "\n")
                                                    self.call_from_thread(output_log.refresh)
                                                    self.call_from_thread(output_log.scroll_end, animate=False)
                                                else:
                                                    self.call_from_thread(output_log.write, line + "\n")
                                                    self.call_from_thread(output_log.refresh)
                                                    self.call_from_thread(output_log.scroll_end, animate=False)
                                except (OSError, BlockingIOError):
                                    pass
                                
                                # Write any remaining buffer
                                if line_buffer:
                                    line = line_buffer.rstrip('\r\n')
                                    if line:
                                        if len(line) > wrap_width:
                                            wrapped_lines = textwrap.wrap(line, width=wrap_width, break_long_words=True, break_on_hyphens=False, replace_whitespace=False)
                                            for wrapped_line in wrapped_lines:
                                                self.call_from_thread(output_log.write, wrapped_line + "\n")
                                            self.call_from_thread(output_log.refresh)
                                            self.call_from_thread(output_log.scroll_end, animate=False)
                                        else:
                                            self.call_from_thread(output_log.write, line + "\n")
                                            self.call_from_thread(output_log.refresh)
                                            self.call_from_thread(output_log.scroll_end, animate=False)
                                break
                            time.sleep(0.01)  # Small sleep to avoid busy waiting
                        except OSError:
                            # File descriptor closed or error
                            break
                except Exception as e:
                    try:
                        self.call_from_thread(output_log.write, f"[red]Error reading output: {e}[/red]\n")
                        self.call_from_thread(output_log.refresh)
                    except:
                        pass
                finally:
                    if use_pty:
                        os.close(read_fd)
                    # For regular pipe, it will be closed when process ends
            
            # Store process reference for polling
            self._current_process = process
            self._current_process_exit_code = None
            
            # Start reading in a background thread
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            
            # Use set_timer to poll process status without blocking
            # This allows the event loop to process queued call_from_thread updates
            def check_process():
                exit_code = process.poll()
                if exit_code is not None:
                    self._current_process_exit_code = exit_code
                    reader_thread.join(timeout=0.5)
                    # Add completion indicator (we're in main thread, so call directly)
                    output_log.write("\n" + "─" * 70 + "\n")
                    if exit_code == 0:
                        output_log.write("Command completed successfully\n")
                    else:
                        output_log.write(f"Command failed with exit code {exit_code}\n")
                    output_log.write("─" * 70 + "\n")
                    output_log.refresh()
                    output_log.scroll_end(animate=False)
                else:
                    # Check again in 50ms - this is non-blocking!
                    self.set_timer(0.05, check_process)
            
            # Start polling (non-blocking)
            self.set_timer(0.05, check_process)
            
            # Return immediately - the polling will set exit code
            # For now return 0, but the actual code will be in self._current_process_exit_code
            return 0
        except Exception as e:
            try:
                self.call_from_thread(output_log.write, f"[bold red]Error: {e}[/bold red]\n")
                self.call_from_thread(output_log.refresh)
            except:
                pass
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
        self._run_command_streaming(["git", "pull"], output_log, sudo=False)
        
        # Wait for the actual exit code
        def check_exit_code():
            if self._current_process_exit_code is not None:
                exit_code = self._current_process_exit_code
                output_log.write("\n")
                if exit_code == 0:
                    output_log.write("[bold green]✓ Git pull completed successfully![/bold green]\n")
                    output_log.write("[yellow]Please restart the TUI to use the latest changes.[/yellow]\n")
                else:
                    output_log.write("[bold red]✗ Git pull failed[/bold red]\n")
            else:
                # Check again in 100ms
                self.set_timer(0.1, check_exit_code)
        
        # Start checking for exit code
        self.set_timer(0.1, check_exit_code)
    
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
