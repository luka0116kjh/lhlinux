#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 ]] || { echo 'Requires Ubuntu 24.04'; exit 1; }
apt-get update
apt-get install -y --no-install-recommends systemd systemd-sysv dbus dbus-user-session libpam-systemd sudo locales ca-certificates curl gnupg \
  bash-completion less nano git ripgrep file binutils gdb build-essential pkg-config libcurl4-openssl-dev \
  python3 python3-venv python3-pip python3-z3 z3 jq unzip xz-utils zstd iproute2 iputils-ping \
  docker.io docker-compose-v2
printf 'lhlinux\n' > /etc/hostname
printf 'LANG=C.UTF-8\n' > /etc/default/locale
cat > /etc/lhlinux-release <<'EOF'
NAME=lhlinux
VERSION=0.1.0
BASE=Ubuntu 24.04 LTS
EDITION=WSL2 CLI
EOF
bash "$(dirname -- "${BASH_SOURCE[0]}")/configure-user.sh"
printf '\nlhlinux 0.1 | Ubuntu 24.04 LTS | Docker + Z3 + binary analysis\nRun lhlinux-help for commands.\n\n' > /etc/motd
systemctl enable docker
