#!/bin/sh
# Wrapper script for manage.py that disables Nix registry lookups
# This prevents warnings about flake-registry.json when offline
export NIX_CONFIG="${NIX_CONFIG:+$NIX_CONFIG }flake-registry ="
exec "$(dirname "$0")/manage.py" "$@"

