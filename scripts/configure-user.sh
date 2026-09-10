#!/usr/bin/env bash
# Configure the public default account; passwords are set interactively elsewhere.
set -euo pipefail
[[ $EUID == 0 && -f /etc/lhlinux-release ]] || { echo 'Run as root inside lhlinux'; exit 1; }
if ! id admin &>/dev/null; then
  if id luka &>/dev/null; then
    [[ ! -e /home/admin && ! -L /home/admin ]] || { echo '/home/admin already exists'; exit 1; }
    if pgrep -u luka >/dev/null; then
      echo 'Close lhlinux sessions and restart this distribution before migrating the user.'
      exit 1
    fi
    usermod -l admin luka
    groupmod -n admin luka
    usermod -d /home/admin -m admin
    # Preserve existing packages when relocating the original Python venv.
    python3 - <<'PY'
from pathlib import Path
folder = Path('/home/admin/lab/.venv/bin')
if folder.is_dir():
    for path in folder.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b'\0' not in data and b'/home/luka/lab/.venv' in data:
            path.write_bytes(data.replace(b'/home/luka/lab/.venv', b'/home/admin/lab/.venv'))
PY
  else
    useradd -m -s /bin/bash admin
  fi
fi
[[ $(getent passwd admin | cut -d: -f6) == /home/admin ]] || { echo 'Unexpected admin home directory'; exit 1; }
usermod -aG sudo,docker admin
printf 'admin ALL=(ALL:ALL) ALL\n' > /etc/sudoers.d/90-lhlinux
chmod 440 /etc/sudoers.d/90-lhlinux
visudo -cf /etc/sudoers.d/90-lhlinux
cat > /etc/wsl.conf <<'EOF'
[boot]
systemd=true
[network]
hostname=lhlinux
[user]
default=admin
EOF
echo 'Default account: admin; set its password with passwd admin as root.'
