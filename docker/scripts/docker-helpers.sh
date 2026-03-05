#!/bin/bash
# docker-helpers.sh — Shared utility functions for CMDS2 Docker environment
#
# Source this file from scripts that need Docker-aware behavior:
#   . /usr/local/lib/cmds2/docker-helpers.sh
#
# All functions are safe to call on bare-metal (they simply return false/noop
# when CMDS_DOCKER is not set).

# Returns 0 (true) when running inside the Docker container.
in_docker() {
  [[ "${CMDS_DOCKER:-0}" == "1" ]]
}

# Returns 0 (true) when the web API layer is driving this script.
in_web_mode() {
  [[ "${CMDS_WEB_MODE:-0}" == "1" ]]
}

# Emit a JSON progress line when running under the web API.
# Usage: web_progress <percent> <message>
web_progress() {
  local pct="${1:-0}" msg="${2:-}"
  if in_web_mode; then
    # Escape double-quotes in message for valid JSON
    msg="${msg//\"/\\\"}"
    printf '{"pct":%d,"msg":"%s"}\n' "$pct" "$msg"
  fi
}

# Docker-safe wrapper for systemctl.
# In Docker, translates to s6-svc commands. On bare-metal, passes through.
docker_service_ctl() {
  local action="$1" service="$2"
  if in_docker; then
    case "$action" in
      start)   s6-svc -u "/run/service/${service}" 2>/dev/null || true ;;
      stop)    s6-svc -d "/run/service/${service}" 2>/dev/null || true ;;
      restart) s6-svc -r "/run/service/${service}" 2>/dev/null || true ;;
      status)
        if s6-svstat "/run/service/${service}" 2>/dev/null | grep -q 'true'; then
          echo "active"
        else
          echo "inactive"
        fi
        ;;
      *)       echo "Unknown action: $action" >&2; return 1 ;;
    esac
  else
    systemctl "$action" "$service"
  fi
}

# Docker-safe reboot: in Docker, this restarts the container (via s6 finish).
# On bare-metal, issues a real reboot.
docker_safe_reboot() {
  if in_docker; then
    echo "Container will restart..."
    # Signal s6-overlay to perform a clean shutdown
    s6-svscanctl -t /run/s6/services 2>/dev/null || kill 1
  else
    reboot
  fi
}
