#!/usr/bin/env bash
# ServiceMan – systemd service manager (dialog UI) — dynamic unit detection
# Docker-aware: when CMDS_DOCKER=1, uses s6-svc instead of systemctl.
set -euo pipefail

# ─── Stable environment for systemctl ─────────────────────────────────────────
export LC_ALL=C
export LANG=C
export SYSTEMD_PAGER=
export SYSTEMD_LESS=
export SYSTEMD_COLORS=0

# ─── Docker detection ───────────────────────────────────────────────────────
in_docker() { [[ "${CMDS_DOCKER:-0}" == "1" ]]; }

# s6-rc service names (systemd unit -> s6 longrun name)
declare -A S6_MAP=(
  [httpd.service]="httpd"
  [tftp-server.socket]="tftpd"
  [atd.service]="atd"
)

# ─── Requirements ─────────────────────────────────────────────────────────────
if ! command -v dialog >/dev/null 2>&1; then
  echo "Error: dialog is required. Install it and retry." >&2
  exit 1
fi

# Consistent backtitle + enable color tags everywhere we call dialog
shopt -s expand_aliases
alias dialog='dialog --backtitle "Service Manager" --colors'

# ─── Admin tool mappings (optional helpers per unit) ──────────────────────────
declare -A SERVICE_ADMIN_TOOLS=(
  [samba.service]="/root/.servman/SambaMan"
  [dhcpd.service]="/root/.servman/dhcp_admin.sh"
  [kea-dhcp4.service]="/root/.server_admin/dhcp_admin.sh"
  [chronyd.service]="/root/.servman/NTPMan/ntp_admin.sh"
  [fail2ban.service]="/root/.servman/jail-admin.sh"
)

# Global candidate list (rebuilt dynamically)
CANDIDATE_UNITS=()

build_candidate_units() {
  if in_docker; then
    # In Docker, only s6-managed services are available
    CANDIDATE_UNITS=(
      httpd.service
      tftp-server.socket
      atd.service
    )
    return
  fi

  # Base services we always care about
  CANDIDATE_UNITS=(
    chronyd.service
    httpd.service
    tftp-server.socket
    fail2ban.service
    named.service
    sshd.service
    cockpit.socket
  )

  # Only add dhcpd if systemd knows about it (unit file exists)
  if systemctl list-unit-files dhcpd.service >/dev/null 2>&1; then
    CANDIDATE_UNITS+=(dhcpd.service)
  fi

  # Only add kea-dhcp4 if unit exists AND Kea config exists
  if systemctl list-unit-files kea-dhcp4.service >/dev/null 2>&1 && \
     [[ -f /etc/kea/kea-dhcp4.conf ]]; then
    CANDIDATE_UNITS+=(kea-dhcp4.service)
  fi
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
service_state() {
  # Return exactly one token: active|inactive|failed|activating|deactivating|reloading|dead|unknown
  local unit="$1"
  if in_docker; then
    local s6name="${S6_MAP[$unit]:-}"
    if [[ -z "$s6name" ]]; then echo "unknown"; return; fi
    if s6-svstat "/run/service/${s6name}" 2>/dev/null | grep -q 'true'; then
      echo "active"
    else
      echo "inactive"
    fi
  else
    local s
    s=$(systemctl is-active "$unit" 2>/dev/null) || true
    echo "${s:-unknown}"
  fi
}

pretty_state() {
  case "$1" in
    active)                  echo "running" ;;
    inactive|dead|unknown)   echo "stopped" ;;
    failed)                  echo "failed/stopped" ;;
    activating|deactivating) echo "transitioning" ;;
    *)                       echo "$1" ;;
  esac
}

style_state() {
  case "$1" in
    running) echo $'\Z2running\Zn' ;;
    stopped) echo $'\Z1stopped\Zn' ;;
    *)       echo $'\Z3'"$1"$'\Zn' ;;
  esac
}

# A unit is "installed/present" if systemd knows about it (rc 0 or 3)
_present_unit() {
  if in_docker; then
    local s6name="${S6_MAP[$1]:-}"
    [[ -n "$s6name" ]] && [[ -d "/run/service/${s6name}" ]] && return 0
    return 1
  fi
  if systemctl status "$1" >/dev/null 2>&1; then
    return 0
  else
    local rc=$?
    [[ $rc -eq 3 ]] && return 0
    return 1
  fi
}

get_installed_units() {
  build_candidate_units  # refresh the candidate list each time

  local installed=() u
  for u in "${CANDIDATE_UNITS[@]}"; do
    # Handle templated patterns here if you add them later
    if [[ "$u" == *'@*.service' ]]; then
      # example expansion block (kept off by default)
      # mapfile -t _tmpl < <(systemctl list-units --all --no-legend --no-pager | awk '{print $1}' | grep -E "^${u/\*/.+}$" || true)
      # installed+=("${_tmpl[@]}")
      :
    else
      if _present_unit "$u"; then
        installed+=("$u")
      fi
    fi
  done
  printf '%s\n' "${installed[@]}"
}

# ─── Unit Control Submenu ─────────────────────────────────────────────────────
control_unit_menu() {
  local unit="$1"
  local admin_script="" has_admin_script=false

  if [[ -n "${SERVICE_ADMIN_TOOLS[$unit]+_}" && -x "${SERVICE_ADMIN_TOOLS[$unit]}" ]]; then
    admin_script="${SERVICE_ADMIN_TOOLS[$unit]}"
    has_admin_script=true
  fi

  while true; do
    local a f label styled header choice rc
    if in_docker; then
      a=$(service_state "$unit")
      f=""
    else
      a=$(systemctl is-active "$unit" 2>/dev/null) || a=""
      f=$(systemctl is-failed "$unit" 2>/dev/null) || f=""
    fi

    if [[ "$f" == "failed" ]]; then
      label="failed/stopped";         styled=$'\Z1failed/stopped\Zn'
    elif [[ "$a" == "active" ]]; then
      label="running";                styled=$'\Z2running\Zn'
    elif [[ "$a" == "inactive" || "$a" == "dead" ]]; then
      label="stopped";                styled=$'\Z1stopped\Zn'
    elif [[ "$a" == "unknown" || "$f" == "unknown" || -z "$a" ]]; then
      label="unknown/stopped";        styled=$'\Z1unknown/stopped\Zn'
    elif [[ "$a" == "activating" || "$a" == "deactivating" || "$a" == "reloading" ]]; then
      label="transitioning";          styled=$'\Z3transitioning\Zn'
    else
      label="unknown/stopped";        styled=$'\Z1unknown/stopped\Zn'
    fi

    header=$'Status: '"$styled"$'\n\nAction:'

    exec 3>&1; set +e
    local options=(
      1 "Start"
      2 "Stop"
      3 "Restart"
      4 "View Logs"
    )
    if [[ "$has_admin_script" == true ]]; then
      options+=(5 "Launch Admin Tool" 6 "Back")
    else
      options+=(5 "Back")
    fi
    choice=$(dialog --clear --title "Manage Unit: $unit" \
                    --menu "$header" 20 70 10 "${options[@]}" \
                    2>&1 1>&3)
    rc=$?; set -e; exec 3>&-
    [[ $rc -ne 0 ]] && break

    case "$choice" in
      1)
         if in_docker; then
           local s6name="${S6_MAP[$unit]:-}"
           [[ -n "$s6name" ]] && s6-svc -u "/run/service/${s6name}" 2>/dev/null
         else
           systemctl start "$unit"
         fi
         dialog --msgbox "$unit started." 6 50 ;;
      2)
         if in_docker; then
           local s6name="${S6_MAP[$unit]:-}"
           [[ -n "$s6name" ]] && s6-svc -d "/run/service/${s6name}" 2>/dev/null
         else
           systemctl stop "$unit"
         fi
         dialog --msgbox "$unit stopped." 6 50 ;;
      3)
         if in_docker; then
           local s6name="${S6_MAP[$unit]:-}"
           [[ -n "$s6name" ]] && s6-svc -r "/run/service/${s6name}" 2>/dev/null
         else
           systemctl restart "$unit"
         fi
         dialog --msgbox "$unit restarted." 6 50 ;;
      4)
         if in_docker; then
           local s6name="${S6_MAP[$unit]:-}"
           if [[ -n "$s6name" ]]; then
             echo "s6-managed service: ${s6name}" > "/tmp/${unit//\//_}_logs.txt"
             s6-svstat "/run/service/${s6name}" >> "/tmp/${unit//\//_}_logs.txt" 2>&1
           else
             echo "No logs available in Docker mode." > "/tmp/${unit//\//_}_logs.txt"
           fi
         else
           journalctl -u "$unit" -n 200 --no-pager > "/tmp/${unit//\//_}_logs.txt"
         fi
         dialog --title "$unit Logs (arrows/PageUp/PageDown)" \
                --tailbox "/tmp/${unit//\//_}_logs.txt" 30 160
         ;;
      5)
         if [[ "$has_admin_script" == true ]]; then
           "$admin_script"
         else
           break
         fi
         ;;
      6) break ;;
    esac
  done
}

# ─── Manage Installed Units ───────────────────────────────────────────────────
manage_units_menu() {
  while true; do
    mapfile -t UNITS < <( get_installed_units )
    if (( ${#UNITS[@]} == 0 )); then
      dialog --msgbox "No candidate units present." 6 60
      break
    fi

    local menu_args=() u s s_disp selected rc
    for u in "${UNITS[@]}"; do
      s=$(service_state "$u")
      case "$s" in
        active)            s_disp=$'\Z2active\Zn' ;;
        inactive|dead)     s_disp=$'\Z1inactive\Zn' ;;
        failed)            s_disp=$'\Z1failed\Zn' ;;
        unknown|'')        s_disp=$'\Z1unknown/stopped\Zn' ;;
        *)                 s_disp=$'\Z3'"$s"$'\Zn' ;;
      esac
      menu_args+=( "$u" "$s_disp" )
    done

    exec 3>&1; set +e
    selected=$(
      dialog --clear \
             --title "Systemd Unit Manager" \
             --menu "Select a unit to manage (Cancel -> back):" \
             20 90 "${#UNITS[@]}" \
             "${menu_args[@]}" \
        2>&1 1>&3
    )
    rc=$?; set -e; exec 3>&-
    [[ $rc -ne 0 ]] && break

    control_unit_menu "$selected"
  done
}

# ─── Enable/Disable Services Submenu ──────────────────────────────────────────
enable_disable_menu() {
  if in_docker; then
    dialog --clear --title "Not Available" \
           --msgbox "Service enable/disable is managed by s6-overlay in Docker mode.\n\nUse View/Manage Services to start/stop individual services." 9 70
    return
  fi
  set +e
  dialog --clear \
         --title "Enable/Disable Services" \
         --msgbox "Launching ntsysv...\n\nUse space to toggle services, then OK to apply." \
         8 60
  ntsysv
  set -e
}

# ─── Top-Level Main Menu ──────────────────────────────────────────────────────
main_menu() {
  while true; do
    local choice rc
    exec 3>&1; set +e
    choice=$(
      dialog --clear --title "Service Manager" \
             --menu "Choose an option (Cancel -> exit):" \
             15 60 3 \
               1 "View/Manage Services" \
               2 "Enable/Disable Services (ntsysv)" \
               3 "Exit" \
        2>&1 1>&3
    )
    rc=$?; set -e; exec 3>&-
    [[ $rc -ne 0 ]] && break

    case "$choice" in
      1) manage_units_menu   ;;
      2) enable_disable_menu ;;
      3) clear; exit 0       ;;
    esac
  done
  clear
}

# ─── Direct jump support (e.g. `ServiceMan samba.service`) ────────────────────
if [[ $# -ge 1 ]]; then
  want="$1"
  [[ "$want" != *.service && "$want" != *.socket ]] && want="${want}.service"
  if _present_unit "$want"; then
    control_unit_menu "$want"
    clear
    exit 0
  fi
fi

# ─── Start UI ─────────────────────────────────────────────────────────────────
main_menu