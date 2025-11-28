# Manage Script Improvement Suggestions

This document contains suggestions to improve the `manage.py` script based on code review.

## Table of Contents
1. [Code Quality & Organization](#code-quality--organization)
2. [Error Handling](#error-handling)
3. [Security](#security)
4. [Performance](#performance)
5. [User Experience](#user-experience)
6. [Testing & Maintainability](#testing--maintainability)
7. [Feature Enhancements](#feature-enhancements)

---

## Code Quality & Organization

### 1. **Extract Command Definitions to Configuration File**
**Current Issue**: All actions are hardcoded in the `ACTIONS` dictionary within the Python file.

**Suggestion**: Move action definitions to a separate JSON/YAML configuration file. This would:
- Make it easier to add/modify actions without touching Python code
- Allow machine-specific action customization
- Enable external configuration management

**Example Structure**:
```yaml
actions:
  nixos:
    - id: switch
      title: "Switch Configuration"
      description: "Apply NixOS configuration immediately"
      dangerous: false
      requires_machine: true
      command: ["sudo", "nixos-rebuild", "switch", "--flake", ".#{machine}"]
```

### 2. **Refactor Large `_run_action` Method**
**Current Issue**: The `_run_action` method is a massive if/elif chain (200+ lines) that's hard to maintain.

**Suggestion**: Use a command registry pattern:
```python
class CommandRegistry:
    def __init__(self):
        self._commands = {}
    
    def register(self, action_id: str, handler: Callable):
        self._commands[action_id] = handler
    
    def execute(self, action_id: str, *args, **kwargs):
        if action_id in self._commands:
            return self._commands[action_id](*args, **kwargs)
        raise ValueError(f"Unknown action: {action_id}")
```

### 3. **Separate Command Execution Logic**
**Current Issue**: Command execution logic is mixed with UI logic.

**Suggestion**: Create a separate `CommandExecutor` class that handles:
- Command building
- Execution
- Output streaming
- Error handling

This would make the code more testable and allow for CLI mode in the future.

### 4. **Reduce Code Duplication**
**Current Issue**: Similar patterns repeated throughout (e.g., spinner management, output logging).

**Suggestion**: Create helper methods:
```python
def _with_spinner(self, func):
    """Context manager for spinner operations."""
    spinner = self.query_one("#spinner", Spinner)
    spinner.start()
    try:
        return func()
    finally:
        spinner.stop()
```

### 5. **Type Hints Consistency**
**Current Issue**: Some methods have type hints, others don't. Return types are often missing.

**Suggestion**: Add comprehensive type hints throughout, including:
- Return types for all methods
- Generic types for collections
- Optional types where appropriate

---

## Error Handling

### 6. **Improve Command Execution Error Handling**
**Current Issue**: In `_run_streaming`, errors are caught but not always handled gracefully. Some commands may fail silently.

**Suggestion**:
- Add timeout handling for all subprocess calls
- Implement retry logic for transient failures (network issues, etc.)
- Better error messages with actionable suggestions
- Log errors to a file for debugging

```python
def _run_streaming(self, cmd: List[str], output_log: OutputLog, 
                   shell: bool = False, timeout: int = 300, 
                   retries: int = 0) -> None:
    """Run command with timeout and retry support."""
    for attempt in range(retries + 1):
        try:
            # ... execution logic ...
            break
        except subprocess.TimeoutExpired:
            if attempt < retries:
                output_log.write_line(f"Timeout, retrying ({attempt + 1}/{retries})...\n")
                continue
            raise
```

### 7. **Handle Missing Dependencies Gracefully**
**Current Issue**: Some commands fail with cryptic errors when dependencies aren't installed.

**Suggestion**: Check for required commands before execution:
```python
def _check_command_available(self, cmd: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(cmd) is not None

def _run_action(self, action_id: str, ...):
    required_commands = self._get_required_commands(action_id)
    missing = [c for c in required_commands if not self._check_command_available(c)]
    if missing:
        output_log.write_line(f"Error: Missing required commands: {', '.join(missing)}\n")
        output_log.write_line(f"Install with: nix-shell -p {' '.join(missing)}\n")
        return
```

### 8. **Better Error Recovery**
**Current Issue**: When a command fails, the UI may be left in an inconsistent state.

**Suggestion**: Implement state recovery:
- Reset spinner state on all error paths
- Clear pending dangerous actions on errors
- Provide "retry" option for failed commands

### 9. **Validate Machine Names**
**Current Issue**: Machine names are used directly in commands without validation.

**Suggestion**: Validate machine names against the flake configuration:
```python
def _validate_machine(self, machine: str) -> bool:
    """Validate that machine exists in flake."""
    try:
        result = subprocess.run(
            ["nix", "flake", "show", "--json"],
            cwd=self.flake_path,
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            machines = data.get("nixosConfigurations", {})
            return machine in machines
    except Exception:
        pass
    return False
```

---

## Security

### 10. **Sanitize User Input**
**Current Issue**: Machine names and other inputs are used directly in shell commands.

**Suggestion**: 
- Validate and sanitize all user inputs
- Use subprocess with list arguments (already done, but ensure consistency)
- Avoid shell=True where possible (already mostly done, good!)

### 11. **Sudo Usage Audit**
**Current Issue**: Sudo is used in many places without clear indication of why.

**Suggestion**:
- Document why sudo is needed for each command
- Consider using `sudo -n` (non-interactive) where appropriate
- Add a check for sudo availability before attempting sudo commands
- Consider caching sudo credentials if possible

### 12. **Command Injection Prevention**
**Current Issue**: Some commands use shell=True with string concatenation.

**Suggestion**: Review all shell=True usages and ensure proper escaping:
```python
# Current (risky):
self._run_streaming(["sh", "-c", f"du -ah / --max-depth=3 2>/dev/null | sort -rh | head -20"], ...)

# Better:
self._run_streaming(["du", "-ah", "/", "--max-depth=3"], ...)
# Then pipe in Python if needed
```

---

## Performance

### 13. **Cache Expensive Operations**
**Current Issue**: Some operations (like listing machines, devShells) are repeated without caching.

**Suggestion**: Implement caching for:
- Machine list detection
- DevShell listing
- Flake metadata
- Command availability checks

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
        return None
    
    def set(self, key: str, value):
        self._cache[key] = (value, datetime.now())
```

### 14. **Lazy Loading of Actions**
**Current Issue**: All actions are loaded at startup, even if never used.

**Suggestion**: Load actions on-demand when tabs are accessed.

### 15. **Optimize Output Streaming**
**Current Issue**: Output is written line-by-line, which may be slow for large outputs.

**Suggestion**: 
- Buffer output and write in chunks
- Implement virtual scrolling for very long outputs
- Add option to limit output size

### 16. **Background Process Management**
**Current Issue**: All commands run in daemon threads, but there's no way to cancel long-running operations.

**Suggestion**: 
- Add ability to cancel running commands (Ctrl+C handling)
- Show process status (running, completed, failed)
- Allow multiple commands to run in parallel (with queue management)

---

## User Experience

### 17. **Search/Filter Actions**
**Current Issue**: With many actions, finding the right one can be difficult.

**Suggestion**: Add search functionality:
- Press `/` to open search
- Filter actions by name/description
- Highlight matching text

### 18. **Command History**
**Current Issue**: No way to see or repeat previous commands.

**Suggestion**: 
- Maintain a history of executed commands
- Allow browsing history with arrow keys
- Quick re-execution of previous commands

### 19. **Progress Indicators for Long Operations**
**Current Issue**: Some operations (like `rebuild-all`) can take a long time with minimal feedback.

**Suggestion**:
- Show progress bars for multi-step operations
- Estimate time remaining
- Show which step is currently executing

### 20. **Better Output Formatting**
**Current Issue**: Output is plain text, could be more readable.

**Suggestion**:
- Use Rich tables for structured data (docker ps, systemctl list-units, etc.)
- Syntax highlighting for code/logs
- Collapsible sections for long outputs
- Color coding for success/warning/error

### 21. **Keyboard Shortcuts Documentation**
**Current Issue**: Many keyboard shortcuts exist but aren't visible.

**Suggestion**:
- Add a help screen (press `?` or `F1`)
- Show available shortcuts in footer
- Context-sensitive help

### 22. **Machine Selection UI**
**Current Issue**: Machine selection is just cycling through a list.

**Suggestion**:
- Show a dropdown/popup for machine selection
- Display machine status (online, offline, etc.)
- Show which machine is currently active

### 23. **Command Preview**
**Current Issue**: Users don't see the exact command that will be executed.

**Suggestion**: 
- Show command preview before execution
- Allow editing command arguments (for advanced users)
- Save command templates

### 24. **Output Export**
**Current Issue**: No way to save command output.

**Suggestion**:
- Add "Save Output" option
- Export to file (text, JSON, etc.)
- Copy to clipboard

---

## Testing & Maintainability

### 25. **Add Unit Tests**
**Current Issue**: No tests visible in the codebase.

**Suggestion**: Add tests for:
- Command building logic
- Error handling
- Machine detection
- Action registry

### 26. **Integration Tests**
**Suggestion**: Create integration tests that:
- Test actual command execution (with mocks)
- Test UI interactions
- Test error scenarios

### 27. **Logging System**
**Current Issue**: No structured logging for debugging.

**Suggestion**: Add logging:
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Log all command executions
logger.info(f"Executing command: {cmd}")
logger.debug(f"Command output: {output}")
logger.error(f"Command failed: {error}")
```

### 28. **Configuration Management**
**Current Issue**: Hardcoded values throughout (timeouts, paths, etc.).

**Suggestion**: Create a configuration system:
```python
@dataclass
class Config:
    command_timeout: int = 300
    flake_path: Path = Path.cwd()
    default_machine: Optional[str] = None
    enable_auto_update: bool = True
    # ... etc
```

### 29. **Documentation**
**Suggestion**: 
- Add docstrings to all public methods
- Document command execution flow
- Create architecture diagram
- Add inline comments for complex logic

### 30. **Version Management**
**Current Issue**: Version is hardcoded as a string.

**Suggestion**: 
- Use `__version__` from a version file
- Auto-increment on release
- Show version in help/about screen

---

## Feature Enhancements

### 31. **Command Aliases**
**Suggestion**: Allow users to create custom command aliases:
```python
ALIASES = {
    "rebuild": "switch",
    "restart-docker": "docker-restart-all",
}
```

### 32. **Command Chaining**
**Suggestion**: Allow executing multiple commands in sequence:
- Create "workflows" or "scripts"
- Save common command sequences
- Conditional execution based on previous results

### 33. **Remote Machine Support**
**Suggestion**: 
- SSH support for managing remote machines
- Connection management UI
- Remote command execution

### 34. **Notifications**
**Suggestion**: 
- Desktop notifications for long-running commands
- Sound alerts for completion/failure
- Email/Slack integration for critical operations

### 35. **Metrics & Monitoring**
**Suggestion**: 
- Track command execution times
- Show statistics (most used commands, success rate, etc.)
- Performance monitoring dashboard

### 36. **Plugin System**
**Suggestion**: Allow external plugins to add new actions:
```python
class Plugin:
    def get_actions(self) -> List[Action]:
        """Return list of actions this plugin provides."""
        pass
    
    def execute(self, action_id: str, **kwargs):
        """Execute an action."""
        pass
```

### 37. **Dry Run Mode**
**Suggestion**: Add a dry-run mode that shows what would be executed without actually running:
```python
def _run_action(self, action_id: str, ..., dry_run: bool = False):
    if dry_run:
        output_log.write_line(f"[DRY RUN] Would execute: {cmd}\n")
        return
    # ... actual execution
```

### 38. **Undo/Redo Support**
**Suggestion**: For reversible operations, provide undo capability:
- Track state changes
- Allow rolling back certain operations
- History of changes

### 39. **Batch Operations**
**Suggestion**: 
- Select multiple actions to execute
- Execute on multiple machines
- Parallel execution where safe

### 40. **Auto-completion**
**Suggestion**: 
- Tab completion for machine names
- Command argument completion
- History-based suggestions

---

## Quick Wins (Easy Improvements)

These are relatively easy to implement and would provide immediate value:

1. **Add command timeouts** - Prevent hanging commands
2. **Improve error messages** - More actionable feedback
3. **Add help screen** - Document keyboard shortcuts
4. **Cache machine detection** - Faster startup
5. **Better spinner management** - Ensure spinner always stops
6. **Output formatting** - Use Rich tables for structured data
7. **Command validation** - Check dependencies before execution
8. **Search functionality** - Quick action lookup
9. **Command history** - Repeat previous commands
10. **Progress indicators** - Better feedback for long operations

---

## Priority Recommendations

### High Priority
1. Extract command definitions to config file (#1)
2. Refactor `_run_action` method (#2)
3. Improve error handling (#6, #7)
4. Add command timeouts (#6)
5. Validate machine names (#9)

### Medium Priority
6. Add search/filter (#17)
7. Command history (#18)
8. Better output formatting (#20)
9. Add unit tests (#25)
10. Logging system (#27)

### Low Priority
11. Plugin system (#36)
12. Remote machine support (#33)
13. Metrics & monitoring (#35)
14. Undo/redo support (#38)

---

## Conclusion

The manage script is well-structured and functional, but there are many opportunities for improvement in terms of maintainability, user experience, and robustness. The suggestions above are organized by priority and impact, allowing for incremental improvements over time.

