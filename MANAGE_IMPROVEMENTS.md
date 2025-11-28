# Manage Script Improvement Recommendations

This document outlines recommended improvements for `manage.py` based on code analysis.

## Table of Contents
1. [Code Organization & Architecture](#code-organization--architecture)
2. [Error Handling & Resilience](#error-handling--resilience)
3. [Performance Optimizations](#performance-optimizations)
4. [Security Enhancements](#security-enhancements)
5. [User Experience](#user-experience)
6. [Testing & Quality Assurance](#testing--quality-assurance)
7. [Documentation](#documentation)
8. [Maintainability](#maintainability)

---

## Code Organization & Architecture

### 1. **Modularize the Monolithic File**
**Current Issue**: The script is 5444 lines in a single file, making it difficult to maintain.

**Recommendations**:
- Split into modules:
  ```
  manage/
  ├── __init__.py
  ├── main.py              # Entry point
  ├── app.py               # ManageApp class
  ├── widgets.py           # Custom widgets (ActionItem, ActionList, etc.)
  ├── commands.py          # CommandRegistry and command handlers
  ├── executor.py          # CommandExecutor class
  ├── cache.py             # CacheManager class
  ├── config.py            # Configuration loading
  ├── screens.py           # Modal screens (HelpScreen, VMCreateWizard, etc.)
  └── utils.py             # Utility functions
  ```
- Use a plugin system for command handlers to make it easier to add new commands
- Create separate modules for each domain (nixos.py, docker.py, system.py, etc.)

### 2. **Separate Configuration from Code**
**Current Issue**: Default actions and tabs are hardcoded in Python.

**Recommendations**:
- Move all default configurations to `manage-actions.yaml` (already exists, but ensure it's the single source of truth)
- Remove duplicate definitions in `_get_default_tabs()` and `_get_default_actions()`
- Add validation for YAML configuration on startup
- Support multiple configuration files (e.g., `manage-actions.local.yaml` for overrides)

### 3. **Implement Command Handler Classes**
**Current Issue**: Command handlers are likely scattered throughout the code.

**Recommendations**:
- Create a base `CommandHandler` abstract class:
  ```python
  class CommandHandler(ABC):
      @abstractmethod
      def execute(self, executor: CommandExecutor, **kwargs) -> int:
          pass
      
      @abstractmethod
      def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
          pass
  ```
- Implement specific handlers: `NixOSCommandHandler`, `DockerCommandHandler`, etc.
- Register handlers in a plugin registry

---

## Error Handling & Resilience

### 4. **Improve Error Recovery**
**Current Issue**: Limited retry logic and error recovery mechanisms.

**Recommendations**:
- Add exponential backoff for retries
- Implement circuit breaker pattern for frequently failing commands
- Add automatic recovery for transient failures (network issues, temporary service unavailability)
- Log errors to a structured log file (JSON format) for better analysis

### 5. **Better Error Messages**
**Current Issue**: Error messages could be more actionable.

**Recommendations**:
- Add context-aware error messages (e.g., "Command failed, but you can try X")
- Include links to documentation or troubleshooting guides
- Show command history for failed commands
- Provide rollback instructions for destructive operations

### 6. **Graceful Degradation**
**Current Issue**: Script may fail completely if dependencies are missing.

**Recommendations**:
- Check for required commands at startup and disable related features if missing
- Show warnings instead of errors for optional dependencies
- Provide fallback modes (e.g., basic mode without TUI if textual is missing)

---

## Performance Optimizations

### 7. **Optimize Command Execution**
**Current Issue**: Commands may block the UI thread.

**Recommendations**:
- Ensure all long-running commands use `execute_async()` consistently
- Add progress indicators for commands that take > 2 seconds
- Implement command cancellation (Ctrl+C handling)
- Add timeout warnings before commands are killed

### 8. **Improve Caching Strategy**
**Current Issue**: CacheManager has a simple TTL-based approach.

**Recommendations**:
- Implement cache invalidation on relevant events (e.g., invalidate Docker cache when containers change)
- Add cache size limits to prevent memory issues
- Use persistent caching for expensive operations (e.g., machine list)
- Add cache statistics and debugging tools

### 9. **Lazy Loading**
**Current Issue**: All commands and actions are loaded at startup.

**Recommendations**:
- Load command handlers on-demand
- Lazy-load machine configurations
- Defer expensive initialization until needed

---

## Security Enhancements

### 10. **Input Validation**
**Current Issue**: Need to verify command arguments are properly sanitized.

**Recommendations**:
- Add input validation for all user-provided arguments
- Sanitize machine names and command arguments
- Prevent command injection by using subprocess with list arguments (already done, but verify all cases)
- Add rate limiting for dangerous operations

### 11. **Permission Checks**
**Current Issue**: Script may attempt operations without proper permissions.

**Recommendations**:
- Check sudo/root requirements before executing commands
- Provide clear error messages when permissions are insufficient
- Add a permission check mode that validates all commands without executing
- Support running in read-only mode for non-privileged users

### 12. **Secure Auto-Update**
**Current Issue**: Auto-update mechanism could be exploited.

**Recommendations**:
- Verify GPG signatures or checksums before applying updates
- Add option to disable auto-updates
- Warn users before auto-updating
- Store update history for audit purposes

---

## User Experience

### 13. **Keyboard Shortcuts**
**Current Issue**: Limited keyboard navigation.

**Recommendations**:
- Add keyboard shortcuts for common actions (e.g., `Ctrl+R` for refresh, `Ctrl+F` for search)
- Implement vim-like navigation (`j`/`k` for up/down, `/` for search)
- Add command palette (`Ctrl+P`) for quick action access
- Support custom keybindings via configuration

### 14. **Better Feedback**
**Current Issue**: Users may not know what's happening during long operations.

**Recommendations**:
- Add progress bars for multi-step operations (e.g., NixOS rebuild)
- Show estimated time remaining for long operations
- Display command output in real-time with syntax highlighting
- Add success/failure notifications with sound or visual indicators

### 15. **Search and Filtering**
**Current Issue**: Search functionality exists but could be enhanced.

**Recommendations**:
- Add fuzzy search for actions
- Support filtering by tags/categories
- Remember recent actions and provide quick access
- Add action history with ability to re-run previous commands

### 16. **Configuration Management**
**Current Issue**: No way to customize the UI or behavior.

**Recommendations**:
- Add user preferences file (e.g., `~/.config/manage/preferences.yaml`)
- Support themes and color schemes
- Allow hiding/showing specific tabs or actions
- Add custom action aliases

---

## Testing & Quality Assurance

### 17. **Add Unit Tests**
**Current Issue**: No visible test suite.

**Recommendations**:
- Create test suite using pytest
- Test command execution logic in isolation
- Mock subprocess calls for testing
- Add integration tests for critical workflows

### 18. **Add Type Checking**
**Current Issue**: Type hints exist but may not be fully utilized.

**Recommendations**:
- Run mypy for static type checking
- Fix all type errors
- Add type stubs for external dependencies
- Use strict type checking in CI/CD

### 19. **Code Quality Tools**
**Current Issue**: No visible linting or formatting standards.

**Recommendations**:
- Add black for code formatting
- Use ruff or pylint for linting
- Add pre-commit hooks
- Set up CI/CD pipeline with quality checks

---

## Documentation

### 20. **Improve Code Documentation**
**Current Issue**: Some functions may lack docstrings.

**Recommendations**:
- Ensure all public functions have comprehensive docstrings
- Add examples to docstrings
- Document command handler interface
- Add architecture documentation

### 21. **User Documentation**
**Current Issue**: Limited user-facing documentation.

**Recommendations**:
- Create user manual with screenshots
- Add tutorial for first-time users
- Document all keyboard shortcuts
- Create troubleshooting guide

### 22. **API Documentation**
**Current Issue**: No clear API for extending the script.

**Recommendations**:
- Document plugin API for adding custom commands
- Create examples of custom command handlers
- Document configuration file format
- Add migration guide for configuration changes

---

## Maintainability

### 23. **Reduce Code Duplication**
**Current Issue**: Likely duplicate code patterns across command handlers.

**Recommendations**:
- Extract common patterns into utility functions
- Create base classes for similar command types
- Use decorators for common functionality (logging, error handling, caching)

### 24. **Improve Logging**
**Current Issue**: Limited structured logging.

**Recommendations**:
- Use Python's logging module instead of print statements
- Add log levels (DEBUG, INFO, WARNING, ERROR)
- Support log rotation
- Add option to export logs for debugging

### 25. **Version Management**
**Current Issue**: Version is hardcoded in multiple places.

**Recommendations**:
- Use single source of truth for version (already have version.py, ensure it's used everywhere)
- Add version check on startup
- Show changelog when version changes
- Support `--version` command-line flag

### 26. **Dependency Management**
**Current Issue**: Dependencies are specified in nix-shell shebang.

**Recommendations**:
- Add `requirements.txt` or `pyproject.toml` for non-Nix users
- Document all dependencies and their purposes
- Pin dependency versions
- Add dependency check on startup

---

## Quick Wins (High Impact, Low Effort)

1. **Add `--help` flag**: Show usage information
2. **Add `--version` flag**: Display version information
3. **Add command-line mode**: Allow running commands without TUI (e.g., `./manage.py nixos switch`)
4. **Improve error messages**: Make them more actionable
5. **Add logging**: Replace print statements with proper logging (16 print() calls found)
6. **Add configuration validation**: Validate YAML on startup and show clear errors
7. **Add dry-run mode**: Show what would be executed without actually running
8. **Add undo functionality**: For reversible operations, allow undo

## Specific Code Issues Found

### 1. **Print Statements Should Use Logging**
**Location**: Lines 43-46, 57-60, 257, 5403-5408

**Issue**: Using `print()` instead of proper logging makes it difficult to control output levels and redirect logs.

**Fix**: Replace with Python's `logging` module:
```python
import logging
logger = logging.getLogger(__name__)
logger.error("Error: textual library not found...")
```

### 2. **Shell=True Usage**
**Location**: Line 629, 639 (and potentially others)

**Issue**: While there's validation for dangerous patterns, `shell=True` is still a security risk.

**Recommendations**:
- Prefer `shell=False` with list arguments whenever possible
- For commands requiring shell features, consider using Python's `shlex.split()` or implementing the logic in Python
- Document why `shell=True` is necessary for each case
- Add unit tests for command injection attempts

### 3. **Inconsistent Error Handling**
**Location**: Various command handlers

**Issue**: Some commands use `subprocess.run()` directly instead of going through `CommandExecutor`.

**Recommendations**:
- Ensure all command execution goes through `CommandExecutor` for consistent error handling
- Audit all 50+ subprocess calls to ensure they use the executor
- Create a wrapper function that enforces this pattern

### 4. **Missing Type Hints in Some Areas**
**Issue**: While type hints are used, some function signatures could be more specific.

**Recommendations**:
- Add return type hints to all functions
- Use `TypedDict` for complex dictionaries (e.g., action definitions)
- Add type hints for callback functions

### 5. **Hardcoded Timeouts**
**Location**: Line 500 (default timeout = 300 seconds)

**Issue**: Fixed timeout may not be appropriate for all commands.

**Recommendations**:
- Make timeouts configurable per command type
- Add timeout configuration to YAML config
- Allow users to override timeouts for specific commands

### 6. **Auto-Update Security**
**Location**: `_check_and_update_script()` function

**Issue**: Auto-update doesn't verify signatures or checksums.

**Recommendations**:
- Add GPG signature verification
- Verify file checksums before applying updates
- Add option to disable auto-updates
- Store update history for audit trail

---

## Priority Recommendations

### High Priority
1. Modularize the codebase (split into modules)
2. Add comprehensive error handling
3. Add unit tests
4. Improve security (input validation, permission checks)
5. Add command-line mode for automation

### Medium Priority
1. Improve caching strategy
2. Add better user feedback (progress bars, notifications)
3. Enhance search and filtering
4. Add configuration management
5. Improve documentation

### Low Priority
1. Add themes and customization
2. Implement plugin system
3. Add advanced keyboard shortcuts
4. Create user manual with screenshots

---

## Implementation Strategy

1. **Phase 1**: Quick wins and critical fixes (security, error handling)
2. **Phase 2**: Code organization (modularization)
3. **Phase 3**: Testing and quality assurance
4. **Phase 4**: User experience improvements
5. **Phase 5**: Advanced features (plugins, themes, etc.)

---

## Notes

- The script is well-structured for a monolithic application
- Good use of Textual framework for TUI
- Command execution is properly abstracted
- Caching mechanism is a good addition
- Auto-update feature is useful but needs security improvements

