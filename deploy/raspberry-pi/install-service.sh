#!/usr/bin/env bash

set -euo pipefail

SERVICE_TEMPLATE_NAME="plant-measurement@.service"
SERVICE_TEMPLATE_SOURCE="plant-measurement@.service.in"
ENVIRONMENT_FILE="/etc/default/plant-measurement"
DEFAULT_MEASUREMENT_NAME="soil_measurement"

usage() {
    cat <<'EOF'
Install the Raspberry Pi soil-moisture logger as a systemd template service.

Usage:
  sudo bash deploy/raspberry-pi/install-service.sh [options]

Options:
  --name NAME          CSV filename prefix/service instance (default: soil_measurement)
  --serial-port PATH   Stable serial path (default: auto-detect /dev/serial/by-id)
  --user USER          Linux account that runs the logger (default: invoking sudo user)
  --repo-dir PATH      Repository checkout (default: inferred from this script)
  --no-start           Install the service without enabling or starting an instance
  -h, --help           Show this help
EOF
}

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

quote_environment_value() {
    local key="$1"
    local value="$2"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    printf '%s="%s"\n' "$key" "$value"
}

escape_sed_replacement() {
    printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

run_as_service_user() {
    runuser -u "$service_user" -- env HOME="$service_home" "$@"
}

measurement_name="$DEFAULT_MEASUREMENT_NAME"
serial_port=""
service_user="${SUDO_USER:-}"
repo_dir=""
start_service=true

while (($# > 0)); do
    case "$1" in
        --name)
            (($# >= 2)) || fail "--name requires a value"
            measurement_name="$2"
            shift 2
            ;;
        --serial-port)
            (($# >= 2)) || fail "--serial-port requires a value"
            serial_port="$2"
            shift 2
            ;;
        --user)
            (($# >= 2)) || fail "--user requires a value"
            service_user="$2"
            shift 2
            ;;
        --repo-dir)
            (($# >= 2)) || fail "--repo-dir requires a value"
            repo_dir="$2"
            shift 2
            ;;
        --no-start)
            start_service=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown option: $1"
            ;;
    esac
done

((EUID == 0)) || fail "run this installer with sudo"
[[ -n "$service_user" ]] || fail "could not determine the service user; pass --user USER"
[[ "$service_user" != "root" ]] || fail "refusing to run the logger as root; pass --user USER"
id "$service_user" >/dev/null 2>&1 || fail "Linux user does not exist: $service_user"

if [[ ! "$measurement_name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    fail "--name must use only letters, digits, dots, underscores, and hyphens"
fi

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$repo_dir" ]]; then
    repo_dir="$(CDPATH= cd -- "$script_dir/../.." && pwd)"
else
    repo_dir="$(CDPATH= cd -- "$repo_dir" && pwd)"
fi

service_source="$script_dir/$SERVICE_TEMPLATE_SOURCE"
requirements_file="$repo_dir/python/requirements.txt"
logger_script="$repo_dir/python/main.py"
venv_dir="$repo_dir/.venv"
venv_python="$venv_dir/bin/python"
output_dir="$repo_dir/python/data"

[[ -f "$service_source" ]] || fail "missing service template: $service_source"
[[ -f "$requirements_file" ]] || fail "missing Python requirements: $requirements_file"
[[ -f "$logger_script" ]] || fail "missing logger script: $logger_script"
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed"
command -v runuser >/dev/null 2>&1 || fail "runuser is not installed"
getent group dialout >/dev/null 2>&1 || fail "the dialout group does not exist"

if [[ -z "$serial_port" ]]; then
    detected_ports=()
    if [[ -d /dev/serial/by-id ]]; then
        mapfile -t detected_ports < <(
            find /dev/serial/by-id -maxdepth 1 -type l -print | sort
        )
    fi

    case "${#detected_ports[@]}" in
        0)
            fail "no stable serial port found; connect the ESP32 or pass --serial-port PATH"
            ;;
        1)
            serial_port="${detected_ports[0]}"
            ;;
        *)
            printf 'Detected multiple serial ports:\n' >&2
            printf '  %s\n' "${detected_ports[@]}" >&2
            fail "choose one with --serial-port PATH"
            ;;
    esac
fi

[[ -e "$serial_port" ]] || fail "serial port does not exist: $serial_port"

service_group="$(id -gn "$service_user")"
service_home="$(getent passwd "$service_user" | cut -d: -f6)"
[[ -n "$service_home" ]] || fail "could not determine the home directory for $service_user"
service_instance="plant-measurement@${measurement_name}.service"

if "$start_service" && systemctl is-active --quiet plant-measurement.service; then
    fail "legacy plant-measurement.service is active; disable it before installing the template"
fi

if "$start_service"; then
    mapfile -t active_instances < <(
        systemctl list-units \
            --type=service \
            --state=active \
            --plain \
            --no-legend \
            'plant-measurement@*.service' \
            | awk '{print $1}'
    )
    for active_instance in "${active_instances[@]}"; do
        if [[ "$active_instance" != "$service_instance" ]]; then
            fail "$active_instance already owns the serial port; stop it before starting $service_instance"
        fi
    done
fi

if [[ ! -x "$venv_python" ]]; then
    printf 'Creating Python virtual environment at %s\n' "$venv_dir"
    run_as_service_user python3 -m venv "$venv_dir"
fi

printf 'Installing Python dependencies\n'
run_as_service_user \
    "$venv_python" -m pip install --disable-pip-version-check -r "$requirements_file"

usermod -a -G dialout "$service_user"
install -d -o "$service_user" -g "$service_group" -m 0750 "$output_dir"

temporary_dir="$(mktemp -d)"
trap 'rm -rf -- "$temporary_dir"' EXIT
rendered_service="$temporary_dir/$SERVICE_TEMPLATE_NAME"
rendered_environment="$temporary_dir/plant-measurement"

escaped_user="$(escape_sed_replacement "$service_user")"
escaped_group="$(escape_sed_replacement "$service_group")"
sed \
    -e "s|@SERVICE_USER@|$escaped_user|g" \
    -e "s|@SERVICE_GROUP@|$escaped_group|g" \
    "$service_source" >"$rendered_service"

{
    quote_environment_value VENV_PYTHON "$venv_python"
    quote_environment_value LOGGER_SCRIPT "$logger_script"
    quote_environment_value SERIAL_PORT "$serial_port"
    quote_environment_value BAUD_RATE "115200"
    quote_environment_value OUTPUT_DIR "$output_dir"
} >"$rendered_environment"

install -m 0644 "$rendered_service" "/etc/systemd/system/$SERVICE_TEMPLATE_NAME"
install -m 0644 "$rendered_environment" "$ENVIRONMENT_FILE"
systemd-analyze verify "/etc/systemd/system/$SERVICE_TEMPLATE_NAME"
systemctl daemon-reload

printf 'Installed %s\n' "/etc/systemd/system/$SERVICE_TEMPLATE_NAME"
printf 'Installed %s\n' "$ENVIRONMENT_FILE"

if "$start_service"; then
    systemctl enable "$service_instance"
    systemctl restart "$service_instance"
    printf 'Started %s\n' "$service_instance"
else
    printf 'Service installed but not started (--no-start).\n'
fi

printf '\nUseful commands:\n'
printf '  systemctl status %s\n' "$service_instance"
printf '  journalctl -u %s -f\n' "$service_instance"
printf '  ls -lht --time-style=long-iso %s\n' "$output_dir"
